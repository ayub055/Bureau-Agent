BEGIN



DROP TABLE IF EXISTS t_aff_obli_mar25;

CREATE TEMP TABLE t_aff_obli_mar25 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    *,
	CASE
    WHEN EL_flag = 1
         AND nvl(MOB,0) < 36
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
        AND nvl(remain_tenor,0) <= 4 THEN 0
        WHEN EL_flag = 1
         AND nvl(MOB,0) < 36
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
            AND nvl(remain_tenor,0) <= 4 THEN 0
            WHEN EL_flag = 1
			AND nvl(MOB,0) < 36
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
            AND nvl(remain_tenor,0) <= 4 THEN 0
            WHEN EL_flag = 1
			AND nvl(MOB,0) < 36
			AND Out_standing_Balance > Sanction_Amount_1 THEN 0
           
            ELSE EMI
        END
    END AS EMI_Bureau_1_topup_1,
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
    -- Step 2: EMI_Bureau_1 logic
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
                AND nvl(mob,0) < 48
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
                AND nvl(mob,0) < 48
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
            nvl(mob,0) > 36
            OR nvl(Out_standing_Balance,0) < Sanction_Amount_1
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
    -- EMI for Other Products
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
    -- Loan on Credit Card
    CASE
        WHEN Loan_Type = 'Loan on Credit Card'
        AND Loan_Status = 'Live'
        AND (
            (Out_standing_Balance > 0)
            OR (
                DATE_CLOSED IS NULL
                AND Out_standing_Balance = 0
                AND nvl(mob,0) < 48
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
    -- EMI_V2 Calculation
	case when EMI_Bureau_1>0 and
	nvl((EMI_Bureau_1::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1
	ELSE EMI_Calculated
    end as EMI_V2,
    
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
        AND nvl(mob,0) < 48 THEN 1
        ELSE 0
    END AS B1,
    -- EMI_V3 Calculation
    CASE
        WHEN KTK_pl_flag2 = 1
        AND EMI_V2 * 4 > Out_standing_Balance THEN 0
        ELSE EMI_V2
    END AS EMI_V3,
    -- Final Affluence EMI
    EMI_V3 * 2 AS final_affl_emi_2,
    -- PL Flag
    CASE
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND Out_standing_Balance = 0 THEN 1
        ELSE 0
    END AS pl_flag2,
    -- Final Affluence EMI 4
    CASE
        WHEN B1 = 0
        AND nvl((Out_standing_Balance::decimal / case when High_Credit_Amount =0 then null else High_Credit_Amount end),0) < 0.15
        AND final_affl_emi_2 > Out_standing_Balance THEN 0
        ELSE EMI_V3
    END AS final_affl_emi_4,
    -- EMI_Calculated_Unsec
    COALESCE(Affu_EMI_PL, 0) + COALESCE(Affu_EMI_BL_unsec, 0) + COALESCE(Affu_EMI_CC_unsec, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_LCC, 0) + COALESCE(Affu_EMI_STPL, 0) + COALESCE(Affu_EMI_OD_unsec, 0) AS EMI_Calculated_Unsec,
    -- EMI_Bureau_unsec_1 adjustment
    CASE
        WHEN EMI_Bureau_unsec_1 IS NULL THEN 0
        ELSE EMI_Bureau_unsec_1
    END AS EMI_Bureau_unsec_1_adj,
    -- EMI_V2_unsec
	
	case when EMI_Bureau_unsec_1>0 and
	nvl((EMI_Bureau_unsec_1::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_unsec_1
	else
	EMI_Calculated_Unsec end as EMI_V2_unsec,
    CASE
        WHEN KTK_pl_flag2 = 1
        AND EMI_V2_unsec * 4 > Out_standing_Balance THEN 0
        ELSE EMI_V2_unsec
    END AS EMI_V3_unsec,
    -- final_affl_emi_2_Unsec
    EMI_V3_unsec * 2 AS final_affl_emi_2_Unsec,
    -- final_affl_emi_4_Unsec
    CASE
        WHEN B1 = 0
			AND (    (High_Credit_Amount IS NULL)
				OR	(High_Credit_Amount = 0)
				OR (Out_standing_Balance::decimal / NULLIF(High_Credit_Amount, 0) < 0.15)
				)
			AND EMI_V3_unsec * 2 > Out_standing_Balance 
		THEN 0
        ELSE EMI_V3_unsec
    END AS final_affl_emi_4_Unsec,
	
	
	CASE
    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 0
         AND nvl(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 20000
         AND nvl(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 40000
         AND nvl(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 75000
         AND nvl(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 100000
         AND nvl(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 200000
         AND nvl(Sanction_Amount_1,0) <= 500000
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
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 0
         AND nvl(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 20000
         AND nvl(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 40000
         AND nvl(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 75000
         AND nvl(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 100000
         AND nvl(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 200000
         AND nvl(Sanction_Amount_1,0) <= 500000
    THEN Sanction_Amount_1 * 0.027

    WHEN fo_flag = 1
         AND Loan_Type = 'Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
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
         AND nvl(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 20000
         AND nvl(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 40000
         AND nvl(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 75000
         AND nvl(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 100000
         AND nvl(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND Out_standing_Balance > 0
         AND Sanction_Amount_1 > 200000
         AND nvl(Sanction_Amount_1,0) <= 500000
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
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 0
         AND nvl(Sanction_Amount_1,0) <= 20000
    THEN Sanction_Amount_1 * 0.33

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 20000
         AND nvl(Sanction_Amount_1,0) <= 40000
    THEN Sanction_Amount_1 * 0.12

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 40000
         AND nvl(Sanction_Amount_1,0) <= 75000
    THEN Sanction_Amount_1 * 0.0930

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 75000
         AND nvl(Sanction_Amount_1,0) <= 100000
    THEN Sanction_Amount_1 * 0.0546

    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 100000
         AND nvl(Sanction_Amount_1,0) <= 200000
    THEN Sanction_Amount_1 * 0.035
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 200000
         AND nvl(Sanction_Amount_1,0) <= 500000
    THEN Sanction_Amount_1 * 0.027
    WHEN Loan_Type = 'Short Term Personal Loan'
         AND Loan_Status = 'Live'
         AND DATE_CLOSED IS NULL
         AND Out_standing_Balance = 0
         AND nvl(MOB,0) < 48
         AND Sanction_Amount_1 > 500000
    THEN Sanction_Amount_1 * 0.022

    ELSE 0
END AS Affu_EMI_STPL_topup,
    -- Step 1: Calculate EMI_Calculated_topup
    COALESCE(Affu_EMI_BL, 0) + COALESCE(Affu_EMI_AL, 0) + COALESCE(Affu_EMI_CV, 0) + COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_GL, 0) + COALESCE(Affu_EMI_HL, 0) + COALESCE(Affu_EMI_Pfsl, 0) + COALESCE(Affu_EMI_Other, 0) + COALESCE(Affu_EMI_PL_topup, 0) + COALESCE(Affu_EMI_STPL_topup, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_LAP, 0) + COALESCE(Affu_EMI_TW, 0) + COALESCE(Affu_EMI_UC, 0) + COALESCE(Affu_EMI_EL, 0) + COALESCE(Affu_EMI_CC, 0) + COALESCE(Affu_EMI_OD, 0) + COALESCE(Affu_EMI_KCC, 0) + COALESCE(Affu_EMI_ELse, 0) AS EMI_Calculated_topup,
    -- Step 2: Handle null EMI_Bureau_1_topup
    COALESCE(EMI_Bureau_1_topup_1, 0) AS EMI_Bureau_1_topup,
    -- Step 3: Calculate EMI_V2_topup
	
	case when EMI_Bureau_1_topup>0 and
	nvl((EMI_Bureau_1_topup::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1_topup
	else
	EMI_Calculated_topup end as EMI_V2_topup,
	
	
    -- Step 4: Calculate final_affl_emi_2_toup
    (EMI_V2_topup * 2) AS final_affl_emi_2_toup,
    -- Step 5: Calculate final_affl_emi_4_topup
    CASE
        WHEN pl_flag2 = 0
		AND ( 		(High_Credit_Amount IS NULL)
				OR	(High_Credit_Amount = 0)
				OR (Out_standing_Balance::decimal / NULLIF(High_Credit_Amount, 0) < 0.15)
				)
        AND final_affl_emi_2_toup > Out_standing_Balance 
		THEN 0
        ELSE EMI_V2_topup
    END AS final_affl_emi_4_topup,
    -- Step 1: Calculate EMI_Calculated_Unsec_topup
    COALESCE(Affu_EMI_PL_topup, 0) + COALESCE(Affu_EMI_BL_unsec, 0) + COALESCE(Affu_EMI_CC_unsec, 0) + COALESCE(Affu_EMI_PMAY, 0) + COALESCE(Affu_EMI_CL, 0) + COALESCE(Affu_EMI_LCC, 0) + COALESCE(Affu_EMI_STPL_topup, 0) + COALESCE(Affu_EMI_OD_unsec, 0) AS EMI_Calculated_Unsec_topup,
    -- Step 2: EMI_V2_unsec_topup
	
	case when EMI_Bureau_1_topup>0 and
	nvl((EMI_Bureau_1_topup::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1_topup
	else
	EMI_Calculated_Unsec_topup end as EMI_V2_unsec_topup,
	
	
    -- Step 3: final_affl_emi2_Unsec_topup
	
	case when EMI_Bureau_1_topup>0 and
	nvl((EMI_Bureau_1_topup::decimal/case when High_Credit_Amount =0 then null else High_Credit_Amount end),0)<0.5 then EMI_Bureau_1_topup * 2
	else
	EMI_Calculated_Unsec_topup * 2 end as final_affl_emi2_Unsec_topup,
	
    -- Step 4: final_affl_emi4_Unsec_topup
	
	CASE
    WHEN pl_flag2 = 0
         AND (      (High_Credit_Amount IS NULL)
				OR	(High_Credit_Amount = 0)
				OR (Out_standing_Balance::decimal / NULLIF(High_Credit_Amount, 0) < 0.15)
				)
         AND final_affl_emi2_Unsec_topup > Out_standing_Balance
    THEN 0
    ELSE EMI_V2_unsec_topup
	END AS final_affl_emi4_Unsec_topup,
    -- Step 5: current_emi
    CASE
        WHEN Loan_Type IN ('Personal Loan', 'Short Term Personal Loan')
        AND UPPER(sector) NOT IN ('NOT DISCLOSED')
        AND nvl(remain_tenor,0) <= 4 THEN EMI
        ELSE 0
    END AS current_emi
FROM
    temp_aff_obli_mar25;

analyze t_aff_obli_mar25; 



END;
