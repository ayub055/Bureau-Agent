-- Bureau-obligation logic, ported VERBATIM from the internal Redshift procedure
-- (tools/obligation/pt1.sql + pt2.sql = sp_bureau_obligation_split1).
-- The bands, rates, filters, exclusions, and 8-step EMI logic are UNCHANGED.
--
-- Only mechanical Redshift -> DuckDB dialect edits were made:
--   * source table repointed to the registered view `tl_input`
--   * per-row TENOR sourced from `params_input.tenor_months` (config OBLIGATION_TENOR_MONTHS);
--     default None -> NULL -> every row hits the source's `WHEN tenor IS NULL THEN 0` branch
--     (faithful: our data has no `tenor` column)
--   * ADD_MONTHS(v_etl_end_date,-1)  ->  scrub_date derived from report_month:
--       (strptime(report_month || '01','%Y%m%d') - INTERVAL 1 DAY)::DATE
--       (== last day of the month before report_month, same as sustained_emi)
--   * DATEDIFF(month,a,b)   -> date_diff('month',a,b)
--   * nvl(x,y)              -> COALESCE(x,y)
--   * `col isnull`          -> `col IS NULL`
--   * CREATE TEMP TABLE     -> CREATE TABLE; dropped diststyle/distkey/sortkey/analyze
--   * dynamic `EXECUTE v_sql` collapsed to static SQL
--   * Redshift LATERAL column-alias references (one giant SELECT) are split into a
--     chain of dependency-ordered stages (s1..s7); each stage only references columns
--     materialised by a prior stage. Expressions are copied byte-for-byte.
--
-- Out-of-scope enrichment removed (SLC salary / LOS income / inflation / imputed
-- income). They only fed `Source_of_Income`, which is defaulted to 1 (documented
-- limitation: HL joint loans ~2-3% higher). With Source_of_Income = 1 the HL joint
-- halving branch never fires, so the t_Bureau_HL* chain + UNION ALL collapse to one
-- SELECT. Data has only `loan_type_new`, which already carries the canonical taxonomy
-- pt2 switches on, so Loan_Type := loan_type_new (pt1's PMAY/KCC remap is then a no-op).

-- ========== base tradeline pull (pt1 t_Bureau; base/report_month filters scoped in Python) ==========
DROP TABLE IF EXISTS sc_obl_bureau;
CREATE TABLE sc_obl_bureau AS
SELECT
    crn,
    report_month,
    date_opened AS DATE_OPENED,
    pay_hist_end_date AS Pay_Hist_End_Date,
    (SELECT tenor_months FROM params_input) AS tenor,
    loan_type_new AS Loan_Type_new,
    ownership_type AS Ownership_type,
    loan_status AS Loan_Status,
    date_closed AS DATE_CLOSED,
    sector,
    loan_type_new AS Loan_Type,           -- data carries only loan_type_new (== canonical taxonomy)
    sanction_amount AS Sanction_Amount,
    out_standing_balance AS Out_standing_Balance,
    emi AS EMI,
    high_credit_amount AS High_Credit_Amount,
    1 AS Source_of_Income,                -- SLC/LOS enrichment out of scope -> default 1
    (strptime(report_month || '01', '%Y%m%d') - INTERVAL 1 DAY)::DATE AS scrub_date
FROM tl_input;

-- ========== derived fields + row filters (pt1 temp_aff_obli_mar25) ==========
DROP TABLE IF EXISTS temp_aff_obli_mar25;
CREATE TABLE temp_aff_obli_mar25 AS
SELECT
    *,
    date_diff('month', (case when DATE_OPENED IS NULL then Pay_Hist_End_Date else DATE_OPENED end), scrub_date) AS mob,
   CASE
    WHEN tenor IS NULL THEN 0
    ELSE tenor - date_diff('month', DATE_OPENED, scrub_date)
    END AS remain_tenor,
    CASE
        WHEN UPPER(sector) = 'NOT DISCLOSED' THEN 1
        WHEN UPPER(sector) <> 'NOT DISCLOSED'
        AND (
            COALESCE(tenor, 0) - date_diff('month', DATE_OPENED, scrub_date)
        ) > 4 THEN 1
        ELSE 0
    END AS fo_flag,
    CASE
        WHEN Ownership_type = 'Joint' THEN (Sanction_Amount::decimal / 2) :: numeric(35, 5)
        ELSE Sanction_Amount
    END AS Sanction_Amount_1,
    CASE
        WHEN Loan_Type = 'Education Loan'
        AND Loan_Status = 'Live' THEN 1
        ELSE 0
    END AS EL_flag
FROM sc_obl_bureau
WHERE
    COALESCE(Ownership_type,'x') NOT IN (
        'Authorised User(refers to supplementary card holder)',
        'Guarantor'
    )
    AND NOT (
        Loan_Status = 'Closed'
        AND DATE_CLOSED IS NOT NULL
    );

-- ========== loan-level engine (pt2 sp_bureau_obligation_split1), stage 1 ==========
-- All columns here depend only on temp_aff_obli_mar25 base/derived columns.
DROP TABLE IF EXISTS sc_obl_s1;
CREATE TABLE sc_obl_s1 AS
SELECT
    *,
    CASE
    WHEN EL_flag = 1
         AND COALESCE(MOB,0) < 36
         AND Out_standing_Balance > Sanction_Amount_1
    THEN 1
    ELSE 0
    END AS EL_flag_1,
    CASE
        WHEN Loan_Type IN (
            'Home Loan',
            'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
            'Property Loan',
            'Credit Card',
            'Kisan Credit Card',
            'Overdraft',
            'Gold Loan',
            'Fleet Card',
            'Temporary Overdraft'
        ) THEN 0
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND UPPER(sector) <> 'NOT DISCLOSED'
        AND COALESCE(remain_tenor,0) <= 4 THEN 0
        WHEN EL_flag = 1
         AND COALESCE(MOB,0) < 36
         AND Out_standing_Balance > Sanction_Amount_1 THEN 0
        ELSE EMI
    END AS EMI_Bureau_topup,
    CASE
        WHEN Ownership_type = 'Joint' THEN CASE
            WHEN Loan_Type IN (
                'Home Loan',
                'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
                'Property Loan',
                'Credit Card',
                'Kisan Credit Card',
                'Overdraft',
                'Gold Loan',
                'Fleet Card',
                'Temporary Overdraft'
            ) THEN 0
            WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
            AND UPPER(sector) <> 'NOT DISCLOSED'
            AND COALESCE(remain_tenor,0) <= 4 THEN 0
            WHEN EL_flag = 1
            AND COALESCE(MOB,0) < 36
            AND Out_standing_Balance > Sanction_Amount_1 THEN 0
            ELSE (CAST(EMI AS numeric(35, 5)) / 2)
        END
        ELSE CASE
            WHEN Loan_Type IN (
                'Home Loan',
                'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
                'Property Loan',
                'Credit Card',
                'Kisan Credit Card',
                'Overdraft',
                'Gold Loan',
                'Fleet Card',
                'Temporary Overdraft'
            ) THEN 0
            WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
            AND UPPER(sector) <> 'NOT DISCLOSED'
            AND COALESCE(remain_tenor,0) <= 4 THEN 0
            WHEN EL_flag = 1
            AND COALESCE(MOB,0) < 36
            AND Out_standing_Balance > Sanction_Amount_1 THEN 0
            ELSE EMI
        END
    END AS EMI_Bureau_1_topup_1,
    -- Step 3: HL_Sanction_Amount logic
    CASE
        WHEN COALESCE(Source_of_Income,0) != 1
        AND Ownership_type = 'Joint' THEN (Sanction_Amount::decimal / 2) :: numeric(35, 5)
        ELSE Sanction_Amount
    END AS HL_Sanction_Amount,
    -- Step 4: EMI_Bureau_unsec logic
    CASE
        WHEN Loan_Type IN (
            'Personal Loan',
            'Business Loan - Priority Sector - Small Business',
            'Business Loan - Priority Sector - Agriculture',
            'Business Loan - Priority Sector - Others',
            'Business Loan Against Bank Deposits',
            'Business Loan General',
            'Business Non-Funded Credit Facility - General',
            'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
            'Business Non-Funded Credit Facility - Priority Sector - Small Business',
            'Business Loan Ã¢â‚¬â€œ General',
            'Business Loan Ã¢â‚¬â€œ Unsecured',
            'Business Loan - General',
            'Business Loan - Unsecured',
            'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
            'Consumer Loan',
            'Loan on Credit Card',
            'Short Term Personal Loan'
        ) THEN EMI
        ELSE 0
    END AS EMI_Bureau_unsec,
    -- Step 5: EMI_Bureau_unsec_1 logic
    CASE
        WHEN Ownership_type = 'Joint' THEN CASE
            WHEN Loan_Type IN (
                'Personal Loan',
                'Business Loan - Priority Sector - Small Business',
                'Business Loan - Priority Sector - Agriculture',
                'Business Loan - Priority Sector - Others',
                'Business Loan Against Bank Deposits',
                'Business Loan General',
                'Business Non-Funded Credit Facility - General',
                'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
                'Business Non-Funded Credit Facility - Priority Sector - Small Business',
                'Business Loan Ã¢â‚¬â€œ General',
                'Business Loan Ã¢â‚¬â€œ Unsecured',
                'Business Loan - General',
                'Business Loan - Unsecured',
                'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
                'Consumer Loan',
                'Loan on Credit Card',
                'Short Term Personal Loan'
            ) THEN (CAST(EMI AS numeric(35, 5)) / 2)
            ELSE 0
        END
        ELSE CASE
            WHEN Loan_Type IN (
                'Personal Loan',
                'Business Loan - Priority Sector - Small Business',
                'Business Loan - Priority Sector - Agriculture',
                'Business Loan - Priority Sector - Others',
                'Business Loan Against Bank Deposits',
                'Business Loan General',
                'Business Non-Funded Credit Facility - General',
                'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
                'Business Non-Funded Credit Facility - Priority Sector - Small Business',
                'Business Loan Ã¢â‚¬â€œ General',
                'Business Loan Ã¢â‚¬â€œ Unsecured',
                'Business Loan - General',
                'Business Loan - Unsecured',
                'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
                'Consumer Loan',
                'Loan on Credit Card',
                'Short Term Personal Loan'
            ) THEN EMI
            ELSE 0
        END
    END AS EMI_Bureau_unsec_1,
    CASE
        WHEN Loan_Type IN (
            'Business Loan - Priority Sector - Small Business',
            'Business Loan - Priority Sector - Agriculture',
            'Business Loan - Priority Sector - Others',
            'Business Loan Against Bank Deposits',
            'Business Loan General',
            'Business Non-Funded Credit Facility - General',
            'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
            'Business Non-Funded Credit Facility - Priority Sector - Small Business',
            'Business Loan Ã¢â‚¬â€œ General',
            'Business Loan Ã¢â‚¬â€œ Unsecured',
            'Business Loan - General',
            'Business Loan - Unsecured',
            'Business Loan - Secured'
        )
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
        WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.05) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 150000 THEN (Sanction_Amount_1 * 0.045) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 150000
            AND Sanction_Amount_1 <= 300000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 300000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.03) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000 THEN (Sanction_Amount_1 * 0.029) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_BL,
    CASE
        WHEN Loan_Type = 'Auto Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.044) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 200000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 200000
            AND Sanction_Amount_1 <= 400000 THEN (Sanction_Amount_1 * 0.024) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 400000
            AND Sanction_Amount_1 <= 700000 THEN (Sanction_Amount_1 * 0.022) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 700000 THEN (Sanction_Amount_1 * 0.018) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_AL,
    CASE
        WHEN Loan_Type = 'Commercial_Vehicle'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 50000 THEN (Sanction_Amount_1 * 0.10) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 50000
            AND Sanction_Amount_1 <= 150000 THEN (Sanction_Amount_1 * 0.068) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 150000
            AND Sanction_Amount_1 <= 300000 THEN (Sanction_Amount_1 * 0.041) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 300000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.033) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000
            AND Sanction_Amount_1 <= 1000000 THEN (Sanction_Amount_1 * 0.032) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 1000000 THEN (Sanction_Amount_1 * 0.028) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_CV,
    CASE
        WHEN Loan_Type = 'Consumer Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 6000 THEN (Sanction_Amount_1 * 0.1750) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 6000
            AND Sanction_Amount_1 <= 10000 THEN (Sanction_Amount_1 * 0.1650) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 10000
            AND Sanction_Amount_1 <= 15000 THEN (Sanction_Amount_1 * 0.1450) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 15000
            AND Sanction_Amount_1 <= 25000 THEN (Sanction_Amount_1 * 0.1150) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 25000
            AND Sanction_Amount_1 <= 50000 THEN (Sanction_Amount_1 * 0.10) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 50000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.09) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000 THEN (Sanction_Amount_1 * 0.0850) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_CL,
    CASE
        WHEN Loan_Type = 'Gold Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0
        AND Sanction_Amount_1 > 0 THEN (Sanction_Amount_1 * 0.10) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_GL,
    -- Loan to Professional
    CASE
        WHEN Loan_Type = 'Loan to Professional'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 15000
            AND Sanction_Amount_1 <= 25000 THEN (Sanction_Amount_1 * 0.097) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 25000
            AND Sanction_Amount_1 <= 50000 THEN (Sanction_Amount_1 * 0.090) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 50000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.055) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 150000 THEN (Sanction_Amount_1 * 0.036) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 150000
            AND Sanction_Amount_1 <= 300000 THEN (Sanction_Amount_1 * 0.028) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 300000 THEN (Sanction_Amount_1 * 0.024) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_Pfsl,
    -- Other
    CASE
        WHEN Loan_Type = 'Other'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 6000 THEN (Sanction_Amount_1 * 1.01) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 6000
            AND Sanction_Amount_1 <= 25000 THEN (Sanction_Amount_1 * 0.1250) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 25000
            AND Sanction_Amount_1 <= 50000 THEN (Sanction_Amount_1 * 0.10) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 50000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.09) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 150000 THEN (Sanction_Amount_1 * 0.066) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 150000
            AND Sanction_Amount_1 <= 300000 THEN (Sanction_Amount_1 * 0.033) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 300000 THEN (Sanction_Amount_1 * 0.022) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_Other,
    -- Personal Loan
    CASE
        WHEN Loan_Type = 'Personal Loan'
        AND Loan_Status = 'Live'
        AND (
            (Out_standing_Balance > 0)
            OR (
                DATE_CLOSED IS NULL
                AND Out_standing_Balance = 0
                AND COALESCE(mob,0) < 48
            )
        ) THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 20000 THEN (Sanction_Amount_1 * 0.33) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 20000
            AND Sanction_Amount_1 <= 40000 THEN (Sanction_Amount_1 * 0.12) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 40000
            AND Sanction_Amount_1 <= 75000 THEN (Sanction_Amount_1 * 0.0930) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 75000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.0546) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 200000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 200000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.027) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000 THEN (Sanction_Amount_1 * 0.022) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_PL,
    -- Short Term Personal Loan
    CASE
        WHEN Loan_Type = 'Short Term Personal Loan'
        AND Loan_Status = 'Live'
        AND (
            (Out_standing_Balance > 0)
            OR (
                DATE_CLOSED IS NULL
                AND Out_standing_Balance = 0
                AND COALESCE(mob,0) < 48
            )
        ) THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 20000 THEN (Sanction_Amount_1 * 0.33) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 20000
            AND Sanction_Amount_1 <= 40000 THEN (Sanction_Amount_1 * 0.12) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 40000
            AND Sanction_Amount_1 <= 75000 THEN (Sanction_Amount_1 * 0.0930) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 75000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.0546) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 200000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 200000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.027) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000 THEN (Sanction_Amount_1 * 0.022) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_STPL,
    -- PMAY CLSS
    CASE
        WHEN Loan_Type = 'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.0128) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000
            AND Sanction_Amount_1 <= 1000000 THEN (Sanction_Amount_1 * 0.0117) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 1000000
            AND Sanction_Amount_1 <= 2000000 THEN (Sanction_Amount_1 * 0.0108) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 2000000
            AND Sanction_Amount_1 <= 3000000 THEN (Sanction_Amount_1 * 0.0099) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 3000000 THEN (Sanction_Amount_1 * 0.0088) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_PMAY,
    -- Property Loan
    CASE
        WHEN Loan_Type = 'Property Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.0150) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000
            AND Sanction_Amount_1 <= 1000000 THEN (Sanction_Amount_1 * 0.0140) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 1000000
            AND Sanction_Amount_1 <= 2000000 THEN (Sanction_Amount_1 * 0.0135) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 2000000
            AND Sanction_Amount_1 <= 3000000 THEN (Sanction_Amount_1 * 0.0130) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 3000000 THEN (Sanction_Amount_1 * 0.0110) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_LAP,
    -- Two-wheeler Loan
    CASE
        WHEN Loan_Type = 'Two-wheeler Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 50000 THEN (Sanction_Amount_1 * 0.0533) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 50000
            AND Sanction_Amount_1 <= 75000 THEN (Sanction_Amount_1 * 0.05) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 75000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.045) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000 THEN (Sanction_Amount_1 * 0.04) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_TW,
    -- Used Car Loan
    CASE
        WHEN Loan_Type = 'Used Car Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.0430) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 200000 THEN (Sanction_Amount_1 * 0.0350) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 200000
            AND Sanction_Amount_1 <= 400000 THEN (Sanction_Amount_1 * 0.0290) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 400000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.0250) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000
            AND Sanction_Amount_1 <= 800000 THEN (Sanction_Amount_1 * 0.0230) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 800000 THEN (Sanction_Amount_1 * 0.0220) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_UC,
    -- Education Loan EMI
    CASE
        WHEN Loan_Type = 'Education Loan'
        AND Loan_Status = 'Live'
        AND (
            COALESCE(mob,0) > 36
            OR COALESCE(Out_standing_Balance,0) < Sanction_Amount_1
        ) THEN (Sanction_Amount_1 * 0.09) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_EL,
    -- Credit Card
    CASE
        WHEN Loan_Type = 'Credit Card'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 100 THEN (Out_standing_Balance * 0.05) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_CC,
    -- Overdraft
    CASE
        WHEN Loan_Type = 'Overdraft'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 100 THEN (Out_standing_Balance * 0.05) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_OD,
    -- Kisan Credit Card
    CASE
        WHEN Loan_Type = 'Kisan Credit Card'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 100 THEN (Out_standing_Balance * 0.05) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_KCC,
    -- Flag for Other Products
    CASE
        WHEN Loan_Type IN (
            'Business Loan - Priority Sector - Small Business',
            'Business Loan - Priority Sector - Agriculture',
            'Business Loan - Priority Sector - Others',
            'Business Loan Against Bank Deposits',
            'Business Loan General',
            'Business Non-Funded Credit Facility - General',
            'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
            'Business Non-Funded Credit Facility - Priority Sector - Small Business',
            'Business Loan Ã¢â‚¬â€œ General',
            'Business Loan Ã¢â‚¬â€œ Unsecured',
            'Business Loan - General',
            'Business Loan - Unsecured',
            'Business Loan - Secured',
            'Auto Loan',
            'Commercial_Vehicle',
            'Consumer Loan',
            'Gold Loan',
            'Home Loan',
            'Loan to Professional',
            'Other',
            'Personal Loan',
            'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
            'Property Loan',
            'Two-wheeler Loan',
            'Used Car Loan',
            'Education Loan',
            'Credit Card',
            'Overdraft',
            'Kisan Credit Card',
            'Short Term Personal Loan'
        ) THEN 0
        ELSE 1
    END AS other_product,
    -- Loan on Credit Card
    CASE
        WHEN Loan_Type = 'Loan on Credit Card'
        AND Loan_Status = 'Live'
        AND (
            (Out_standing_Balance > 0)
            OR (
                DATE_CLOSED IS NULL
                AND Out_standing_Balance = 0
                AND COALESCE(mob,0) < 48
            )
        ) THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 20000 THEN (Sanction_Amount_1 * 0.33) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 20000
            AND Sanction_Amount_1 <= 40000 THEN (Sanction_Amount_1 * 0.12) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 40000
            AND Sanction_Amount_1 <= 75000 THEN (Sanction_Amount_1 * 0.0930) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 75000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.0546) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 200000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 200000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.027) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000 THEN (Sanction_Amount_1 * 0.022) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_LCC,
    -- Business Loan EMI Calculation
    CASE
        WHEN Loan_Type IN (
            'Business Loan - Priority Sector - Small Business',
            'Business Loan - Priority Sector - Agriculture',
            'Business Loan - Priority Sector - Others',
            'Business Loan Against Bank Deposits',
            'Business Loan General',
            'Business Non-Funded Credit Facility - General',
            'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
            'Business Non-Funded Credit Facility - Priority Sector - Small Business',
            'Business Loan Ã¢â‚¬â€œ General',
            'Business Loan Ã¢â‚¬â€œ Unsecured',
            'Business Loan - General',
            'Business Loan - Unsecured'
        )
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0
        AND Sanction_Amount_1 > 0 THEN CASE
            WHEN Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.05) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 150000 THEN (Sanction_Amount_1 * 0.045) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 150000
            AND Sanction_Amount_1 <= 300000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 300000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.03) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000 THEN (Sanction_Amount_1 * 0.029) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_BL_unsec,
    -- Credit Card EMI Calculation
    CASE
        WHEN Loan_Type IN ('Credit Card', 'Fleet Card', 'Kisan Credit Card')
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 100 THEN (Out_standing_Balance * 0.05) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_CC_unsec,
    -- Overdraft EMI Calculation
    CASE
        WHEN Loan_Type IN ('Overdraft', 'Temporary Overdraft')
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 100 THEN (Out_standing_Balance * 0.05) :: numeric(35, 5)
        ELSE 0
    END AS Affu_EMI_OD_unsec,
    -- KTK Flag
    CASE
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND UPPER(sector) NOT IN ('NOT DISCLOSED') THEN 1
        ELSE 0
    END AS KTK_pl_flag2,
    -- B1 Flag
    CASE
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND Loan_Status = 'Live'
        AND DATE_CLOSED IS NULL
        AND Out_standing_Balance = 0
        AND COALESCE(mob,0) < 48 THEN 1
        ELSE 0
    END AS B1,
    -- PL Flag
    CASE
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND Out_standing_Balance = 0 THEN 1
        ELSE 0
    END AS pl_flag2,
    CASE
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 0
         AND COALESCE(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 20000
         AND COALESCE(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 40000
         AND COALESCE(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 75000
         AND COALESCE(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 100000
         AND COALESCE(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 200000
         AND COALESCE(Sanction_Amount_1,0) <= 500000
    THEN Sanction_Amount_1 * 0.027
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 500000
    THEN Sanction_Amount_1 * 0.022
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 0
         AND COALESCE(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 20000
         AND COALESCE(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 40000
         AND COALESCE(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 75000
         AND COALESCE(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 100000
         AND COALESCE(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 200000
         AND COALESCE(Sanction_Amount_1,0) <= 500000
    THEN Sanction_Amount_1 * 0.027
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 500000
    THEN Sanction_Amount_1 * 0.022
    ELSE 0
    END AS Affu_EMI_PL_topup,
    CASE
    -- Live STPL with positive balance
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 0
         AND COALESCE(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 20000
         AND COALESCE(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 40000
         AND COALESCE(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 75000
         AND COALESCE(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 100000
         AND COALESCE(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 200000
         AND COALESCE(Sanction_Amount_1,0) <= 500000
    THEN Sanction_Amount_1 * 0.027
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 500000
    THEN Sanction_Amount_1 * 0.022
    -- Live STPL closed with zero balance and mob < 48
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 0
         AND COALESCE(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 20000
         AND COALESCE(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 40000
         AND COALESCE(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 75000
         AND COALESCE(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 100000
         AND COALESCE(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 200000
         AND COALESCE(Sanction_Amount_1,0) <= 500000
    THEN Sanction_Amount_1 * 0.027
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND COALESCE(MOB,0) < 48
         AND Sanction_Amount_1 > 500000
    THEN Sanction_Amount_1 * 0.022
    ELSE 0
    END AS Affu_EMI_STPL_topup,
    -- current_emi
    CASE
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND UPPER(sector) NOT IN ('NOT DISCLOSED')
        AND COALESCE(remain_tenor,0) <= 4 THEN EMI
        ELSE 0
    END AS current_emi
FROM temp_aff_obli_mar25;

-- ========== stage 2: columns referencing stage-1 aliases ==========
DROP TABLE IF EXISTS sc_obl_s2;
CREATE TABLE sc_obl_s2 AS
SELECT
    *,
    CASE
        WHEN Loan_Type IN (
            'Home Loan',
            'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
            'Property Loan',
            'Credit Card',
            'Kisan Credit Card',
            'Overdraft',
            'Gold Loan',
            'Fleet Card',
            'Temporary Overdraft'
        ) THEN 0
        WHEN EL_flag_1 = 1 THEN 0
        ELSE EMI
    END AS EMI_Bureau,
    CASE
        WHEN Ownership_type = 'Joint' THEN CASE
            WHEN Loan_Type IN (
                'Home Loan',
                'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
                'Property Loan',
                'Credit Card',
                'Kisan Credit Card',
                'Overdraft',
                'Gold Loan',
                'Fleet Card',
                'Temporary Overdraft'
            )
            OR EL_flag_1 = 1 THEN 0
            ELSE (CAST(EMI AS numeric(35, 5)) / 2)
        END
        ELSE CASE
            WHEN Loan_Type IN (
                'Home Loan',
                'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS',
                'Property Loan',
                'Credit Card',
                'Kisan Credit Card',
                'Overdraft',
                'Gold Loan',
                'Fleet Card',
                'Temporary Overdraft'
            )
            OR EL_flag_1 = 1 THEN 0
            ELSE EMI
        END
    END AS EMI_Bureau_1,
    -- Home Loan (uses HL_Sanction_Amount from stage 1)
    CASE
        WHEN Loan_Type = 'Home Loan'
        AND Loan_Status = 'Live'
        AND Out_standing_Balance > 0 THEN CASE
            WHEN HL_Sanction_Amount > 0
            AND HL_Sanction_Amount <= 500000 THEN (HL_Sanction_Amount * 0.0130) :: numeric(35, 5)
            WHEN HL_Sanction_Amount > 500000
            AND HL_Sanction_Amount <= 1000000 THEN (HL_Sanction_Amount * 0.0117) :: numeric(35, 5)
            WHEN HL_Sanction_Amount > 1000000
            AND HL_Sanction_Amount <= 2000000 THEN (HL_Sanction_Amount * 0.0110) :: numeric(35, 5)
            WHEN HL_Sanction_Amount > 2000000
            AND HL_Sanction_Amount <= 3000000 THEN (HL_Sanction_Amount * 0.01) :: numeric(35, 5)
            WHEN HL_Sanction_Amount > 3000000 THEN (HL_Sanction_Amount * 0.0088) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_HL,
    -- EMI for Other Products (uses other_product from stage 1)
    CASE
        WHEN Loan_Status = 'Live'
        AND Out_standing_Balance > 0
        AND other_product = 1 THEN CASE
            WHEN Sanction_Amount_1 > 0
            AND Sanction_Amount_1 <= 50000 THEN (Sanction_Amount_1 * 0.06) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 50000
            AND Sanction_Amount_1 <= 100000 THEN (Sanction_Amount_1 * 0.05) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 100000
            AND Sanction_Amount_1 <= 300000 THEN (Sanction_Amount_1 * 0.045) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 300000
            AND Sanction_Amount_1 <= 500000 THEN (Sanction_Amount_1 * 0.035) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 500000
            AND Sanction_Amount_1 <= 1000000 THEN (Sanction_Amount_1 * 0.032) :: numeric(35, 5)
            WHEN Sanction_Amount_1 > 1000000 THEN (Sanction_Amount_1 * 0.028) :: numeric(35, 5)
            ELSE 0
        END
        ELSE 0
    END AS Affu_EMI_ELse,
    -- EMI_Bureau_unsec_1 adjustment
    CASE
        WHEN EMI_Bureau_unsec_1 IS NULL THEN 0
        ELSE EMI_Bureau_unsec_1
    END AS EMI_Bureau_unsec_1_adj,
    -- Step 2: Handle null EMI_Bureau_1_topup
    COALESCE(EMI_Bureau_1_topup_1, 0) AS EMI_Bureau_1_topup
FROM sc_obl_s1;

-- ========== stage 3: aggregate EMI_Calculated* and EMI_Bureau_1_adj ==========
DROP TABLE IF EXISTS sc_obl_s3;
CREATE TABLE sc_obl_s3 AS
SELECT
    *,
    (COALESCE(Affu_EMI_BL, 0) + COALESCE(Affu_EMI_AL, 0) + COALESCE(Affu_EMI_CV, 0) +
        COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_GL, 0) + COALESCE(Affu_EMI_HL, 0) +
        COALESCE(Affu_EMI_Pfsl, 0) + COALESCE(Affu_EMI_Other, 0) + COALESCE(Affu_EMI_PL, 0) +
        COALESCE(Affu_EMI_STPL, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_LAP, 0) +
        COALESCE(Affu_EMI_TW, 0) + COALESCE(Affu_EMI_UC, 0) + COALESCE(Affu_EMI_EL, 0) +
        COALESCE(Affu_EMI_CC, 0) + COALESCE(Affu_EMI_OD, 0) + COALESCE(Affu_EMI_KCC, 0) +
        COALESCE(Affu_EMI_ELse, 0) ) AS EMI_Calculated,
    -- EMI Bureau Adjustment
    CASE
        WHEN EMI_Bureau_1 IS NULL THEN 0
        ELSE EMI_Bureau_1
    END AS EMI_Bureau_1_adj,
    -- EMI_Calculated_Unsec
    COALESCE(Affu_EMI_PL, 0) + COALESCE(Affu_EMI_BL_unsec, 0) + COALESCE(Affu_EMI_CC_unsec, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_LCC, 0) + COALESCE(Affu_EMI_STPL, 0) + COALESCE(Affu_EMI_OD_unsec, 0) AS EMI_Calculated_Unsec,
    -- EMI_Calculated_topup
    COALESCE(Affu_EMI_BL, 0) + COALESCE(Affu_EMI_AL, 0) + COALESCE(Affu_EMI_CV, 0) + COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_GL, 0) + COALESCE(Affu_EMI_HL, 0) + COALESCE(Affu_EMI_Pfsl, 0) + COALESCE(Affu_EMI_Other, 0) + COALESCE(Affu_EMI_PL_topup, 0) + COALESCE(Affu_EMI_STPL_topup, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_LAP, 0) + COALESCE(Affu_EMI_TW, 0) + COALESCE(Affu_EMI_UC, 0) + COALESCE(Affu_EMI_EL, 0) + COALESCE(Affu_EMI_CC, 0) + COALESCE(Affu_EMI_OD, 0) + COALESCE(Affu_EMI_KCC, 0) + COALESCE(Affu_EMI_ELse, 0) AS EMI_Calculated_topup,
    -- EMI_Calculated_Unsec_topup
    COALESCE(Affu_EMI_PL_topup, 0) + COALESCE(Affu_EMI_BL_unsec, 0) + COALESCE(Affu_EMI_CC_unsec, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_LCC, 0) + COALESCE(Affu_EMI_STPL_topup, 0) + COALESCE(Affu_EMI_OD_unsec, 0) AS EMI_Calculated_Unsec_topup
FROM sc_obl_s2;

-- ========== stage 4: EMI_V2* (uses EMI_Bureau_1/EMI_Bureau_1_topup + EMI_Calculated*) ==========
DROP TABLE IF EXISTS sc_obl_s4;
CREATE TABLE sc_obl_s4 AS
SELECT
    *,
    case when EMI_Bureau_1>0 and
    COALESCE((EMI_Bureau_1::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1
    ELSE EMI_Calculated
    end as EMI_V2,
    -- EMI_V2_unsec
    case when EMI_Bureau_unsec_1>0 and
    COALESCE((EMI_Bureau_unsec_1::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_unsec_1
    else
    EMI_Calculated_Unsec end as EMI_V2_unsec,
    -- EMI_V2_topup
    case when EMI_Bureau_1_topup>0 and
    COALESCE((EMI_Bureau_1_topup::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1_topup
    else
    EMI_Calculated_topup end as EMI_V2_topup,
    -- EMI_V2_unsec_topup
    case when EMI_Bureau_1_topup>0 and
    COALESCE((EMI_Bureau_1_topup::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1_topup
    else
    EMI_Calculated_Unsec_topup end as EMI_V2_unsec_topup,
    -- final_affl_emi2_Unsec_topup
    case when EMI_Bureau_1_topup>0 and
    COALESCE((EMI_Bureau_1_topup::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1_topup * 2
    else
    EMI_Calculated_Unsec_topup * 2 end as final_affl_emi2_Unsec_topup
FROM sc_obl_s3;

-- ========== stage 5: EMI_V3*, final_affl_emi_2_toup, final_affl_emi4_Unsec_topup ==========
DROP TABLE IF EXISTS sc_obl_s5;
CREATE TABLE sc_obl_s5 AS
SELECT
    *,
    -- EMI_V3
    CASE
        WHEN KTK_pl_flag2 = 1
        AND EMI_V2 * 4 > Out_standing_Balance THEN 0
        ELSE EMI_V2
    END AS EMI_V3,
    -- EMI_V3_unsec
    CASE
        WHEN KTK_pl_flag2 = 1
        AND EMI_V2_unsec * 4 > Out_standing_Balance THEN 0
        ELSE EMI_V2_unsec
    END AS EMI_V3_unsec,
    -- final_affl_emi_2_toup
    (EMI_V2_topup * 2) AS final_affl_emi_2_toup,
    -- final_affl_emi4_Unsec_topup
    CASE
    WHEN pl_flag2 = 0
         AND (      (High_Credit_Amount IS NULL)
                OR  (High_Credit_Amount = 0)
                OR (Out_standing_Balance::decimal / NULLIF(High_Credit_Amount, 0) < 0.15)
                )
         AND final_affl_emi2_Unsec_topup > Out_standing_Balance
    THEN 0
    ELSE EMI_V2_unsec_topup
    END AS final_affl_emi4_Unsec_topup
FROM sc_obl_s4;

-- ========== stage 6: final_affl_emi_2(_Unsec), final_affl_emi_4_Unsec, final_affl_emi_4_topup ==========
DROP TABLE IF EXISTS sc_obl_s6;
CREATE TABLE sc_obl_s6 AS
SELECT
    *,
    -- Final Affluence EMI
    EMI_V3 * 2 AS final_affl_emi_2,
    -- final_affl_emi_2_Unsec
    EMI_V3_unsec * 2 AS final_affl_emi_2_Unsec,
    -- final_affl_emi_4_Unsec
    CASE
        WHEN B1 = 0
            AND (    (High_Credit_Amount IS NULL)
                OR  (High_Credit_Amount = 0)
                OR (Out_standing_Balance::decimal / NULLIF(High_Credit_Amount, 0) < 0.15)
                )
            AND EMI_V3_unsec * 2 > Out_standing_Balance
        THEN 0
        ELSE EMI_V3_unsec
    END AS final_affl_emi_4_Unsec,
    -- final_affl_emi_4_topup
    CASE
        WHEN pl_flag2 = 0
        AND (       (High_Credit_Amount IS NULL)
                OR  (High_Credit_Amount = 0)
                OR (Out_standing_Balance::decimal / NULLIF(High_Credit_Amount, 0) < 0.15)
                )
        AND final_affl_emi_2_toup > Out_standing_Balance
        THEN 0
        ELSE EMI_V2_topup
    END AS final_affl_emi_4_topup
FROM sc_obl_s5;

-- ========== stage 7: final_affl_emi_4 (uses final_affl_emi_2) ==========
DROP TABLE IF EXISTS sc_obl_s7;
CREATE TABLE sc_obl_s7 AS
SELECT
    *,
    -- Final Affluence EMI 4
    CASE
        WHEN B1 = 0
        AND COALESCE((Out_standing_Balance::decimal / case when High_Credit_Amount =0 then null else High_Credit_Amount end),0) < 0.15
        AND final_affl_emi_2 > Out_standing_Balance THEN 0
        ELSE EMI_V3
    END AS final_affl_emi_4
FROM sc_obl_s6;

-- ========== final CRN-level aggregation (pt1 BUREAU_OBLIGATION insert) ==========
DROP TABLE IF EXISTS sc_obligation_final;
CREATE TABLE sc_obligation_final AS
SELECT
    crn,
    report_month,
    SUM(final_affl_emi_4)          AS aff_emi,
    SUM(final_affl_emi_4_Unsec)    AS emi_unsec,
    SUM(final_affl_emi_4_topup)    AS aff_emi_topup,
    SUM(final_affl_emi4_Unsec_topup) AS emi_unsec_topup,
    SUM(current_emi)               AS current_emi
FROM sc_obl_s7
GROUP BY crn, report_month;
