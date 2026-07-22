-- Bureau income logic, ported VERBATIM from Bureau.ipynb (cells 1-28).
-- Only mechanical Snowflake -> DuckDB dialect edits were made:
--   * source table repointed to the registered view `tl_input`
--   * to_date(x,'YYYYMMDD')      -> strptime(x,'%Y%m%d')::DATE
--   * DATEADD(day,-1,d)          -> (d - INTERVAL 1 DAY)::DATE
--   * DATEDIFF(month,a,b)        -> date_diff('month',a,b)
--   * GREATEST(...) on DPDF*     -> "+ (sum)*0" to emulate Snowflake NULL-poisoning
--   * "INDEX"/"YEAR" quoted (DuckDB keywords)
--   * hardcoded report_month / BASE filters dropped (scoped in Python)
--   * occupation source repointed to the registered view `occupation_input`
-- The affluence bands, divisors, caps and thresholds are UNCHANGED.

-- ========== CELL 1: base tradeline pull ==========
DROP TABLE IF EXISTS sc_rl_final;
CREATE TABLE sc_rl_final AS
SELECT DISTINCT
 Loan_Status
,Loan_Type_new
,Sanction_Amount
,High_Credit_Amount
,CREDITLIMIT
,DATE_OPENED
,DATE_CLOSED
,Pay_Hist_Start_Date
,Ownership_type
,Over_due_amount
,Dpd_string
,Sector
,a.CRN
,report_month
,report_month || '01' AS report_month_date
FROM tl_input A;

-- ========== CELL 7: DPD string cleanup + DPDF1..DPDF36 ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_may25;
CREATE TABLE sc_CIBIL_Aff_may25 AS
WITH replace_dpd AS (
    SELECT
        *,
        CASE WHEN loan_status = 'Live' THEN Pay_Hist_Start_Date
            ELSE DATE_CLOSED
        END AS dpd_date_new
        ,(strptime(report_month_date,'%Y%m%d') - INTERVAL 1 DAY)::DATE AS scrub_date,
        REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(
                                REPLACE(DPD_STRING, 'STD', '000'),
                            'XXX', '000'),
                        'DBT', '090'),
                    'LSS', '090'),
                'SMA', '090'),
            'SUB', '090'),
        ' ', '') AS REPLACED_STRING
    FROM sc_rl_final
)
SELECT *,
date_diff('month', dpd_date_new, scrub_date) AS TL_VIN_1,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 1, 3)), '') AS INT) AS DPDF1,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 4, 3)), '') AS INT) AS DPDF2,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 7, 3)), '') AS INT) AS DPDF3,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 10, 3)), '') AS INT) AS DPDF4,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 13, 3)), '') AS INT) AS DPDF5,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 16, 3)), '') AS INT) AS DPDF6,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 19, 3)), '') AS INT) AS DPDF7,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 22, 3)), '') AS INT) AS DPDF8,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 25, 3)), '') AS INT) AS DPDF9,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 28, 3)), '') AS INT) AS DPDF10,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 31, 3)), '') AS INT) AS DPDF11,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 34, 3)), '') AS INT) AS DPDF12,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 37, 3)), '') AS INT) AS DPDF13,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 40, 3)), '') AS INT) AS DPDF14,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 43, 3)), '') AS INT) AS DPDF15,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 46, 3)), '') AS INT) AS DPDF16,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 49, 3)), '') AS INT) AS DPDF17,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 52, 3)), '') AS INT) AS DPDF18,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 55, 3)), '') AS INT) AS DPDF19,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 58, 3)), '') AS INT) AS DPDF20,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 61, 3)), '') AS INT) AS DPDF21,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 64, 3)), '') AS INT) AS DPDF22,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 67, 3)), '') AS INT) AS DPDF23,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 70, 3)), '') AS INT) AS DPDF24,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 73, 3)), '') AS INT) AS DPDF25,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 76, 3)), '') AS INT) AS DPDF26,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 79, 3)), '') AS INT) AS DPDF27,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 82, 3)), '') AS INT) AS DPDF28,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 85, 3)), '') AS INT) AS DPDF29,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 88, 3)), '') AS INT) AS DPDF30,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 91, 3)), '') AS INT) AS DPDF31,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 94, 3)), '') AS INT) AS DPDF32,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 97, 3)), '') AS INT) AS DPDF33,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 100, 3)), '') AS INT) AS DPDF34,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 103, 3)), '') AS INT) AS DPDF35,
CAST(NULLIF(TRIM(SUBSTRING(REPLACED_STRING, 106, 3)), '') AS INT) AS DPDF36
FROM replace_dpd;

-- ========== CELL 9: Max DPD + reported-window flags ==========
-- "+ (sum)*0" poisons the result to NULL if any DPDF is NULL (Snowflake GREATEST semantics).
DROP TABLE IF EXISTS sc_CIBIL_Aff_may25_1;
CREATE TABLE sc_CIBIL_Aff_may25_1 AS
SELECT *,
    GREATEST(DPDF1, DPDF2, DPDF3, DPDF4, DPDF5, DPDF6)
      + (DPDF1+DPDF2+DPDF3+DPDF4+DPDF5+DPDF6)*0 AS Max_DPD,
    GREATEST(DPDF1,DPDF2,DPDF3,DPDF4,DPDF5,DPDF6,DPDF7,DPDF8,DPDF9,DPDF10,DPDF11,DPDF12,DPDF13,DPDF14,DPDF15,DPDF16,DPDF17,DPDF18,DPDF19,DPDF20,DPDF21,DPDF22,DPDF23,DPDF24,DPDF25,DPDF26,DPDF27,DPDF28,DPDF29,DPDF30,DPDF31,DPDF32,DPDF33,DPDF34,DPDF35,DPDF36)
      + (DPDF1+DPDF2+DPDF3+DPDF4+DPDF5+DPDF6+DPDF7+DPDF8+DPDF9+DPDF10+DPDF11+DPDF12+DPDF13+DPDF14+DPDF15+DPDF16+DPDF17+DPDF18+DPDF19+DPDF20+DPDF21+DPDF22+DPDF23+DPDF24+DPDF25+DPDF26+DPDF27+DPDF28+DPDF29+DPDF30+DPDF31+DPDF32+DPDF33+DPDF34+DPDF35+DPDF36)*0 AS TL_Max_DPD,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 THEN 1 ELSE 0 END AS latest_DPD_6m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 THEN 1 ELSE 0 END AS HL_latest_DPD_3m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 THEN 1 ELSE 0 END AS AL_latest_DPD_9m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 THEN 1 ELSE 0 END AS PL_latest_DPD_12m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 THEN 1 ELSE 0 END AS BL_latest_DPD_12m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 THEN 1 ELSE 0 END AS LAP_latest_DPD_12m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 AND DPDF13 >= 0 AND DPDF14 >= 0 AND DPDF15 >= 0 AND DPDF16 >= 0 AND DPDF17 >= 0 AND DPDF18 >= 0 THEN 1 ELSE 0 END AS CC_CL_latest_DPD_18m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 AND DPDF13 >= 0 AND DPDF14 >= 0 AND DPDF15 >= 0 AND DPDF16 >= 0 AND DPDF17 >= 0 AND DPDF18 >= 0 THEN 1 ELSE 0 END AS CC_HSCA_latest_DPD_18m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 THEN 1 ELSE 0 END AS CVTLCE_latest_DPD_12m,
    CASE WHEN DPDF1 >= 0 AND DPDF2 >= 0 AND DPDF3 >= 0 AND DPDF4 >= 0 AND DPDF5 >= 0 AND DPDF6 >= 0 AND DPDF7 >= 0 AND DPDF8 >= 0 AND DPDF9 >= 0 AND DPDF10 >= 0 AND DPDF11 >= 0 AND DPDF12 >= 0 THEN 1 ELSE 0 END AS LTP_latest_DPD_12m
FROM sc_CIBIL_Aff_may25;

-- ========== CELL 11: filter + joint-halved sanction ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_may25_2;
CREATE TABLE sc_CIBIL_Aff_may25_2 AS
SELECT *
       , CASE
           WHEN Ownership_type = 'Joint' THEN SANCTION_AMOUNT / 2
           ELSE SANCTION_AMOUNT
         END AS SANCTION_AMOUNT_new
FROM sc_CIBIL_Aff_may25_1
WHERE coalesce(MAX_DPD,0) < 15
  AND coalesce(Over_due_amount,0) < 2500
  AND Ownership_type NOT IN ('Guarantor', 'Authorised User(refers to supplementary card holder)');

-- ========== CELL 13: per-CRN max sanction by loan type ==========
DROP TABLE IF EXISTS sc_cc;
CREATE TABLE sc_cc AS
SELECT
    crn,
    COUNT(crn) AS crn_count,
    COUNT(CASE WHEN UPPER(sector) = 'NOT DISCLOSED' AND LOAN_TYPE_NEW = 'Credit Card' AND loan_status = 'Live' THEN crn END) AS cc_count,
    COUNT(CASE WHEN LOAN_TYPE_NEW <> 'Credit Card' THEN crn END) AS other_cc_count,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW = 'Housing Loan' AND HL_latest_DPD_3m > 0 THEN SANCTION_AMOUNT END) AS max_HL,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW = 'Property Loan' AND LAP_latest_DPD_12m > 0 THEN SANCTION_AMOUNT END) AS max_LAP,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW IN ('Commercial Vehicle Loan', 'Construction Equipment Loan') AND CVTLCE_latest_DPD_12m > 0 THEN SANCTION_AMOUNT END) AS max_CVCE,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW IN (
                    'Business Loan - General', 'Business Loan - Priority Sector - Agriculture',
                    'Business Loan - Priority Sector - Others', 'Business Loan - Priority Sector - Small Business',
                    'Business Loan - Secured', 'Business Loan - Unsecured', 'Business Loan Against Bank Deposits',
                    'Business Non-Funded Credit Facility - Priority Sector-Others',
                    'Business Non-Funded Credit Facility - General',
                    'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
                    'Business Non-Funded Credit Facility - Priority Sector - Small Business',
                    'Business Loan – General', 'Business Loan – Unsecured'
                 ) AND BL_latest_DPD_12m > 0 THEN SANCTION_AMOUNT END) AS max_BL,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW = 'Personal Loan' AND UPPER(sector) = 'NOT DISCLOSED' AND PL_latest_DPD_12m > 0 THEN SANCTION_AMOUNT_new END) AS max_PL,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW = 'Auto Loan (Personal)' AND AL_latest_DPD_9m > 0 THEN SANCTION_AMOUNT_new END) AS max_AL,
    MAX(CASE WHEN loan_status = 'Live' AND UPPER(sector) = 'NOT DISCLOSED' AND LOAN_TYPE_NEW = 'Credit Card' AND CC_CL_latest_DPD_18m > 0 THEN CreditLimit END) AS max_CC_CL,
    MAX(CASE WHEN loan_status = 'Live' AND UPPER(sector) = 'NOT DISCLOSED' AND LOAN_TYPE_NEW = 'Credit Card' AND CC_HSCA_latest_DPD_18m > 0 THEN High_Credit_Amount END) AS max_CC_HCA,
    MAX(CASE WHEN TL_VIN_1 <= 36 AND LOAN_TYPE_NEW = 'Loan to Professional' AND LTP_latest_DPD_12m > 0 THEN SANCTION_AMOUNT_new END) AS max_LTP
FROM sc_CIBIL_Aff_may25_2
GROUP BY crn;

-- ========== CELL 14: join per-CRN maxes back onto tradelines ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_may25_3;
CREATE TABLE sc_CIBIL_Aff_may25_3 AS
SELECT a.*
,b.crn_count
,b.cc_count
,b.other_cc_count
,b.max_HL
,b.max_LAP
,b.max_CVCE
,b.max_BL
,b.max_PL
,b.max_AL
,b.max_CC_CL
,b.max_CC_HCA
,b.max_LTP
FROM sc_CIBIL_Aff_may25_2 a LEFT JOIN sc_cc b ON a.crn = b.crn;

-- ========== CELL 15: flag the max tradeline + BL_FLAG + joint halving ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC;
CREATE TABLE sc_CIBIL_Aff_oct_NC AS
WITH sub AS (
SELECT *,
    CASE WHEN SANCTION_AMOUNT = max_HL THEN max_HL ELSE 0 END AS max_HL_1,
    CASE WHEN SANCTION_AMOUNT = max_LAP THEN max_LAP ELSE 0 END AS max_LAP_1,
    CASE WHEN SANCTION_AMOUNT = max_BL THEN max_BL ELSE 0 END AS max_BL_1,
    CASE WHEN SANCTION_AMOUNT = max_CVCE THEN max_CVCE ELSE 0 END AS max_CVCE_1,
    CASE WHEN SANCTION_AMOUNT_new = max_PL THEN max_PL ELSE 0 END AS max_PL_1,
    CASE WHEN SANCTION_AMOUNT_new = max_AL THEN max_AL ELSE 0 END AS max_AL_1,
    CASE WHEN CreditLimit = max_CC_CL THEN max_CC_CL ELSE 0 END AS max_CC_CL_1,
    CASE WHEN High_Credit_Amount = max_CC_HCA THEN max_CC_HCA ELSE 0 END AS max_CC_HCA_1,
    CASE WHEN SANCTION_AMOUNT_new = max_LTP THEN max_LTP ELSE 0 END AS max_LTP_1,
CASE
    WHEN LOAN_TYPE_NEW IN (
        'Business Loan - General', 'Business Loan - Priority Sector - Agriculture',
        'Business Loan - Priority Sector - Others', 'Business Loan - Priority Sector - Small Business',
        'Business Loan - Secured', 'Business Loan - Unsecured', 'Business Loan - Priority Sector',
        'Business Non-Funded Credit Facility - Priority Sector-Others',
        'Business Loan Against Bank Deposits', 'Business Loan General',
        'Business Non-Funded Credit Facility - General',
        'Business Non-Funded Credit Facility - Priority Sector - Agriculture',
        'Business Non-Funded Credit Facility - Priority Sector - Small Business',
        'Business Loan – General', 'Business Loan – Unsecured'
    ) THEN 1
    ELSE 0
END AS BL_FLAG
FROM sc_CIBIL_Aff_may25_3
)
SELECT *,
CASE WHEN Ownership_type = 'Joint' THEN max_HL_1 / 2 ELSE max_HL_1 END AS max_HL_2,
CASE WHEN Ownership_type = 'Joint' THEN max_LAP_1 / 2 ELSE max_LAP_1 END AS max_LAP_2,
CASE WHEN Ownership_type = 'Joint' THEN max_BL_1 / 2 ELSE max_BL_1 END AS max_BL_2
FROM sub;

-- ========== CELL 17: max affluence per loan type (banded) ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC_1;
CREATE TABLE sc_CIBIL_Aff_oct_NC_1 AS
SELECT *,
    CASE
    WHEN UPPER(sector) = 'NOT DISCLOSED'
         AND PL_latest_DPD_12m > 0
         AND LOAN_TYPE_NEW = 'Personal Loan'
         AND TL_VIN_1 <= 36
         AND Ownership_type IN ('Individual', 'Joint') THEN
        CASE
            WHEN max_PL_1 BETWEEN 10000 AND 24999 THEN LEAST(max_PL_1 / 2.5, 10000)
            WHEN max_PL_1 BETWEEN 25000 AND 49999 THEN LEAST(max_PL_1 / 3, 16667)
            WHEN max_PL_1 BETWEEN 50000 AND 99999 THEN LEAST(max_PL_1 / 4, 25000)
            WHEN max_PL_1 BETWEEN 100000 AND 224999 THEN LEAST(max_PL_1 / 5.66, 39719)
            WHEN max_PL_1 BETWEEN 225000 AND 324999 THEN LEAST(max_PL_1 / 7.65, 42510)
            WHEN max_PL_1 BETWEEN 325000 AND 429999 THEN LEAST(max_PL_1 / 10, 43000)
            WHEN max_PL_1 BETWEEN 430000 AND 529999 THEN LEAST(max_PL_1 / 11, 48182)
            WHEN max_PL_1 BETWEEN 530000 AND 649999 THEN LEAST(max_PL_1 / 12.5, 52000)
            WHEN max_PL_1 BETWEEN 650000 AND 829999 THEN LEAST(max_PL_1 / 14, 59286)
            WHEN max_PL_1 BETWEEN 830000 AND 1049999 THEN LEAST(max_PL_1 / 16, 65625)
            WHEN max_PL_1 BETWEEN 1050000 AND 1499999 THEN LEAST(max_PL_1 / 18.72, 80128)
            WHEN max_PL_1 >= 1500000 THEN LEAST(max_PL_1 / 20, 250000)
            ELSE 0
        END
    ELSE 0
END AS PL_MAX_AFFL,
    CASE
        WHEN UPPER(sector) = 'NOT DISCLOSED' AND CC_CL_latest_DPD_18m > 0 AND LOAN_TYPE_NEW = 'Credit Card' AND LOAN_STATUS = 'Live' THEN
            CASE
                WHEN date_opened >= '2022-01-01' AND max_CC_CL_1 BETWEEN 10000 AND 229945 THEN LEAST(max_CC_CL_1 / 4,57486)
                WHEN max_CC_CL_1 BETWEEN 10000 AND 29999 THEN LEAST(max_CC_CL_1 / 1.5, 20000)
                WHEN max_CC_CL_1 BETWEEN 30000 AND 49949 THEN LEAST(max_CC_CL_1 / 1.75, 28543)
                WHEN max_CC_CL_1 BETWEEN 49950 AND 66999 THEN LEAST(max_CC_CL_1 / 1.9, 35263)
                WHEN max_CC_CL_1 BETWEEN 67000 AND 87599 THEN LEAST(max_CC_CL_1 / 2.2, 39818)
                WHEN max_CC_CL_1 BETWEEN 87600 AND 107999 THEN LEAST(max_CC_CL_1 / 2.5, 43200)
                WHEN max_CC_CL_1 BETWEEN 108000 AND 134999 THEN LEAST(max_CC_CL_1 / 2.7, 50000)
                WHEN max_CC_CL_1 BETWEEN 135000 AND 174999 THEN LEAST(max_CC_CL_1 / 3, 58333)
                WHEN max_CC_CL_1 BETWEEN 175000 AND 229945 THEN LEAST(max_CC_CL_1 / 3.5, 65699)
                WHEN max_CC_CL_1 BETWEEN 229946 AND 332999 THEN LEAST(max_CC_CL_1 / 4.12, 80775)
                WHEN max_CC_CL_1 >= 333000 THEN LEAST(max_CC_CL_1 / 4.5, 250000)
                ELSE 0
            END
        ELSE 0
    END AS CC_CL_MAX_AFFL,
    CASE
        WHEN CC_HSCA_latest_DPD_18m > 0 AND LOAN_TYPE_NEW = 'Credit Card' AND LOAN_STATUS = 'Live' THEN
            CASE
                WHEN date_opened >= '2022-01-01' AND max_CC_HCA_1 BETWEEN 10000 AND 282551 THEN LEAST(max_CC_HCA_1 / 4,70637)
                WHEN max_CC_HCA_1 BETWEEN 10000 AND 29595 THEN LEAST(max_CC_HCA_1 / 1.3, 22766)
                WHEN max_CC_HCA_1 BETWEEN 29596 AND 44757 THEN LEAST(max_CC_HCA_1 / 1.3, 34429)
                WHEN max_CC_HCA_1 BETWEEN 44758 AND 59700 THEN LEAST(max_CC_HCA_1 / 1.3, 45924)
                WHEN max_CC_HCA_1 BETWEEN 59701 AND 76511 THEN LEAST(max_CC_HCA_1 / 1.44, 52963)
                WHEN max_CC_HCA_1 BETWEEN 76512 AND 95795 THEN LEAST(max_CC_HCA_1 / 1.69, 56774)
                WHEN max_CC_HCA_1 BETWEEN 95796 AND 116337 THEN LEAST(max_CC_HCA_1 / 1.93, 60314)
                WHEN max_CC_HCA_1 BETWEEN 116338 AND 146633 THEN LEAST(max_CC_HCA_1 / 2.32, 63337)
                WHEN max_CC_HCA_1 BETWEEN 146634 AND 193617 THEN LEAST(max_CC_HCA_1 / 2.68, 72153)
                WHEN max_CC_HCA_1 BETWEEN 193618 AND 282551 THEN LEAST(max_CC_HCA_1 / 3.4, 82989)
                WHEN max_CC_HCA_1 >= 282552 THEN LEAST(max_CC_HCA_1 / 4, 250000)
                ELSE 0
            END
        ELSE 0
    END AS CC_HCA_MAX_AFFL,
    CASE
        WHEN AL_latest_DPD_9m > 0 AND LOAN_TYPE_NEW = 'Auto Loan (Personal)' AND TL_VIN_1 <= 36 THEN
            CASE
                WHEN Ownership_type = 'Individual' OR Ownership_type = 'Joint' THEN
                    CASE
                        WHEN max_AL_1 BETWEEN 10000 AND 279999 THEN LEAST(max_AL_1 / 7.75, 36129)
                        WHEN max_AL_1 BETWEEN 280000 AND 381899 THEN LEAST(max_AL_1 / 10, 38190)
                        WHEN max_AL_1 BETWEEN 381900 AND 454762 THEN LEAST(max_AL_1 / 11, 41342)
                        WHEN max_AL_1 BETWEEN 454763 AND 515999 THEN LEAST(max_AL_1 / 12, 43000)
                        WHEN max_AL_1 BETWEEN 516000 AND 749698 THEN LEAST(max_AL_1 / 13, 57669)
                        WHEN max_AL_1 BETWEEN 749699 AND 869999 THEN LEAST(max_AL_1 / 14, 62143)
                        WHEN max_AL_1 BETWEEN 870000 AND 1055451 THEN LEAST(max_AL_1 / 15, 70363)
                        WHEN max_AL_1 >= 1055452 THEN LEAST(max_AL_1 / 17, 250000)
                        ELSE 0
                    END
                ELSE 0
            END
        ELSE 0
    END AS Al_MAX_AFFL,
CASE
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Housing Loan' AND TL_VIN_1 <= 36 AND max_HL_2 < 100000 THEN 0
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Housing Loan' AND TL_VIN_1 <= 36 AND Ownership_type = 'Individual' AND max_HL_1 <= 2500000 THEN LEAST((max_HL_1 * 0.015) / 0.5, 1000000)
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Housing Loan' AND TL_VIN_1 <= 36 AND Ownership_type = 'Individual' AND max_HL_1 > 2500000 THEN LEAST((max_HL_1 * 0.01) / 0.5, 1000000)
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Housing Loan' AND TL_VIN_1 <= 36 AND Ownership_type = 'Joint' AND max_HL_1 <= 2500000 THEN LEAST(((max_HL_1 * 0.015) / 0.5) / 2, 1000000)
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Housing Loan' AND TL_VIN_1 <= 36 AND Ownership_type = 'Joint' AND max_HL_1 > 2500000 THEN LEAST(((max_HL_1 * 0.01) / 0.5) / 2, 1000000)
    ELSE 0
END AS HL_MAX_AFFL,
CASE
    WHEN LAP_latest_DPD_12m > 0 AND LOAN_TYPE_NEW = 'Property Loan' AND TL_VIN_1 <= 36 AND max_LAP_2 < 100000 THEN 0
    WHEN LAP_latest_DPD_12m > 0 AND LOAN_TYPE_NEW = 'Property Loan' AND TL_VIN_1 <= 36 AND Ownership_type = 'Individual' THEN LEAST(max_LAP_1 * 0.015, 200000)
    WHEN LAP_latest_DPD_12m > 0 AND LOAN_TYPE_NEW = 'Property Loan' AND TL_VIN_1 <= 36 AND Ownership_type = 'Joint' THEN LEAST((max_LAP_1 * 0.015) / 2, 200000)
    ELSE 0
END AS LAP_MAX_AFFL,
CASE
    WHEN BL_latest_DPD_12m > 0 AND BL_FLAG = 1 AND TL_VIN_1 <= 36 AND max_BL_2 < 10000 THEN 0
    WHEN BL_latest_DPD_12m > 0 AND BL_FLAG = 1 AND TL_VIN_1 <= 36 AND Ownership_type = 'Individual' AND max_BL_1 >= 10000 THEN LEAST(GREATEST(max_BL_1 * 0.05, 10000), 200000)
    WHEN BL_latest_DPD_12m > 0 AND BL_FLAG = 1 AND TL_VIN_1 <= 36 AND Ownership_type = 'Joint' AND max_BL_1 >= 10000 THEN LEAST(GREATEST((max_BL_1 * 0.05) / 2, 10000), 200000)
    ELSE 0
END AS BL_MAX_AFFL,
CASE
    WHEN CVTLCE_latest_DPD_12m > 0 AND LOAN_TYPE_NEW IN ('Commercial Vehicle Loan', 'Construction Equipment Loan') AND TL_VIN_1 <= 36 AND Ownership_type = 'Individual' AND max_CVCE_1 > 10000 THEN LEAST(max_CVCE_1 * 0.01, 200000)
    WHEN CVTLCE_latest_DPD_12m > 0 AND LOAN_TYPE_NEW IN ('Commercial Vehicle Loan', 'Construction Equipment Loan') AND TL_VIN_1 <= 36 AND Ownership_type = 'Joint' AND max_CVCE_1 > 10000 THEN LEAST((max_CVCE_1 * 0.01) / 2, 200000)
    ELSE 0
END AS CVCE_MAX_AFFL,
CASE
    WHEN LTP_latest_DPD_12m > 0
         AND LOAN_TYPE_NEW = 'Loan to Professional'
         AND TL_VIN_1 <= 36
         AND Ownership_type IN ('Individual', 'Joint')
         AND max_LTP_1 >= 500000
            THEN 50000
    ELSE 0
END AS LTP_MAX_AFFL
FROM sc_CIBIL_Aff_oct_NC;

-- ========== CELL 18: min/floor affluence per loan type + CC caps ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC_2;
CREATE TABLE sc_CIBIL_Aff_oct_NC_2 AS
SELECT *,
  CASE
    WHEN UPPER(sector) = 'NOT DISCLOSED' AND PL_latest_DPD_12m > 0 AND LOAN_TYPE_NEW = 'Personal Loan' AND TL_VIN_1 <= 36 THEN
      CASE
        WHEN Ownership_type = 'Individual' THEN
          CASE
            WHEN max_PL_1 BETWEEN 10000 AND 24999 THEN 10000
            WHEN max_PL_1 BETWEEN 25000 AND 49999 THEN 10000
            WHEN max_PL_1 BETWEEN 50000 AND 99999 THEN 16667
            WHEN max_PL_1 BETWEEN 100000 AND 224999 THEN 25000
            WHEN max_PL_1 BETWEEN 225000 AND 324999 THEN 39719
            WHEN max_PL_1 BETWEEN 325000 AND 429999 THEN 42510
            WHEN max_PL_1 BETWEEN 430000 AND 529999 THEN 43000
            WHEN max_PL_1 BETWEEN 530000 AND 649999 THEN 48182
            WHEN max_PL_1 BETWEEN 650000 AND 829999 THEN 52000
            WHEN max_PL_1 BETWEEN 830000 AND 1049999 THEN 59286
            WHEN max_PL_1 BETWEEN 1050000 AND 1499999 THEN 65625
            WHEN max_PL_1 BETWEEN 1500000 AND 99999999 THEN 80128
            ELSE 0
          END
        WHEN Ownership_type = 'Joint' THEN
          CASE
            WHEN max_PL_1 BETWEEN 10000 AND 24999 THEN 10000
            WHEN max_PL_1 BETWEEN 25000 AND 49999 THEN 10000
            WHEN max_PL_1 BETWEEN 50000 AND 99999 THEN 16667
            WHEN max_PL_1 BETWEEN 100000 AND 224999 THEN 25000
            WHEN max_PL_1 BETWEEN 225000 AND 324999 THEN 39719
            WHEN max_PL_1 BETWEEN 325000 AND 429999 THEN 42510
            WHEN max_PL_1 BETWEEN 430000 AND 529999 THEN 43000
            WHEN max_PL_1 BETWEEN 530000 AND 649999 THEN 48182
            WHEN max_PL_1 BETWEEN 650000 AND 829999 THEN 52000
            WHEN max_PL_1 BETWEEN 830000 AND 1049999 THEN 59286
            WHEN max_PL_1 BETWEEN 1050000 AND 1499999 THEN 65625
            WHEN max_PL_1 BETWEEN 1500000 AND 99999999 THEN 80128
            ELSE 0
          END
        ELSE 0
      END
    ELSE 0
  END AS PL_min_AFFL,
  CASE
    WHEN UPPER(sector) = 'NOT DISCLOSED' AND CC_CL_latest_DPD_18m > 0 AND LOAN_TYPE_NEW = 'Credit Card' AND LOAN_STATUS = 'Live' THEN
      CASE
        WHEN date_opened >= '2022-01-01' THEN CC_CL_MAX_AFFL
        WHEN max_CC_CL_1 BETWEEN 10000 AND 29999 THEN 10000
        WHEN max_CC_CL_1 BETWEEN 30000 AND 49949 THEN 20000
        WHEN max_CC_CL_1 BETWEEN 49950 AND 66999 THEN 28543
        WHEN max_CC_CL_1 BETWEEN 67000 AND 87599 THEN 35263
        WHEN max_CC_CL_1 BETWEEN 87600 AND 107999 THEN 39818
        WHEN max_CC_CL_1 BETWEEN 108000 AND 134999 THEN 43200
        WHEN max_CC_CL_1 BETWEEN 135000 AND 174999 THEN 50000
        WHEN max_CC_CL_1 BETWEEN 175000 AND 229945 THEN 58333
        WHEN max_CC_CL_1 BETWEEN 229946 AND 332999 THEN 65699
        WHEN max_CC_CL_1 BETWEEN 333000 AND 4129999 THEN 80775
        ELSE 0
      END
    ELSE 0
  END AS CC_CL_min_AFFL,
  CASE
    WHEN CC_CL_latest_DPD_18m > 0 AND LOAN_TYPE_NEW = 'Credit Card' AND LOAN_STATUS = 'Live' THEN
      CASE
        WHEN date_opened >= '2022-01-01' THEN CC_HCA_MAX_AFFL
        WHEN max_CC_HCA_1 BETWEEN 10000 AND 29595 THEN 10000
        WHEN max_CC_HCA_1 BETWEEN 29596 AND 44757 THEN 22766
        WHEN max_CC_HCA_1 BETWEEN 44758 AND 59700 THEN 34429
        WHEN max_CC_HCA_1 BETWEEN 59701 AND 76511 THEN 45924
        WHEN max_CC_HCA_1 BETWEEN 76512 AND 95795 THEN 52963
        WHEN max_CC_HCA_1 BETWEEN 95796 AND 116337 THEN 56774
        WHEN max_CC_HCA_1 BETWEEN 116338 AND 146633 THEN 60314
        WHEN max_CC_HCA_1 BETWEEN 146634 AND 193617 THEN 63337
        WHEN max_CC_HCA_1 BETWEEN 193618 AND 282551 THEN 72153
        WHEN max_CC_HCA_1 BETWEEN 282552 AND 3474874 THEN 82989
        ELSE 0
      END
    ELSE 0
  END AS CC_HCA_min_AFFL,
  CASE
    WHEN AL_latest_DPD_9m > 0 AND LOAN_TYPE_NEW = 'Auto Loan (Personal)' AND TL_VIN_1 <= 36 THEN
      CASE
        WHEN Ownership_type = 'Individual' THEN
          CASE
            WHEN max_AL_1 BETWEEN 10000 AND 279999 THEN 10000
            WHEN max_AL_1 BETWEEN 280000 AND 381899 THEN 36129
            WHEN max_AL_1 BETWEEN 381900 AND 454762 THEN 38190
            WHEN max_AL_1 BETWEEN 454763 AND 515999 THEN 41342
            WHEN max_AL_1 BETWEEN 516000 AND 749698 THEN 43000
            WHEN max_AL_1 BETWEEN 749699 AND 869999 THEN 57669
            WHEN max_AL_1 BETWEEN 870000 AND 1055451 THEN 62143
            WHEN max_AL_1 BETWEEN 1055452 AND 9999999 THEN 70363
            ELSE 0
          END
        WHEN Ownership_type = 'Joint' THEN
          CASE
            WHEN max_AL_1 BETWEEN 10000 AND 279999 THEN 10000
            WHEN max_AL_1 BETWEEN 280000 AND 381899 THEN 36129
            WHEN max_AL_1 BETWEEN 381900 AND 454762 THEN 38190
            WHEN max_AL_1 BETWEEN 454763 AND 515999 THEN 41342
            WHEN max_AL_1 BETWEEN 516000 AND 749698 THEN 43000
            WHEN max_AL_1 BETWEEN 749699 AND 869999 THEN 57669
            WHEN max_AL_1 BETWEEN 870000 AND 1055451 THEN 62143
            WHEN max_AL_1 BETWEEN 1055452 AND 9999999 THEN 70363
            ELSE 0
          END
        ELSE 0
      END
    ELSE 0
  END AS Al_min_AFFL,
  CASE
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Housing Loan' AND TL_VIN_1 <= 36 AND max_HL_2 >= 100000 THEN 10000
    ELSE 0
  END AS HL_min_AFFL,
  CASE
    WHEN HL_latest_DPD_3m > 0 AND LOAN_TYPE_NEW = 'Property Loan' AND TL_VIN_1 <= 36 AND max_LAP_2 >= 100000 THEN 10000
    ELSE 0
  END AS LAP_min_AFFL,
  CASE
    WHEN UPPER(sector) = 'NOT DISCLOSED' AND CC_CL_latest_DPD_18m > 0 AND LOAN_TYPE_NEW = 'Credit Card' AND cc_count = crn_count AND CC_CL_max_AFFL > 150000 THEN 150000
    ELSE CC_CL_max_AFFL
  END AS CC_CL_max_AFFL_n,
  CASE
    WHEN UPPER(sector) = 'NOT DISCLOSED' AND CC_HSCA_latest_DPD_18m > 0 AND LOAN_TYPE_NEW = 'Credit Card' AND cc_count = crn_count AND CC_HCA_max_AFFL > 150000 THEN 150000
    ELSE CC_HCA_max_AFFL
  END AS CC_HCA_max_AFFL_n
FROM sc_CIBIL_Aff_oct_NC_1;

-- ========== CELL 19: greatest(max,min) per type + LOAN_YR ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC_3;
CREATE TABLE sc_CIBIL_Aff_oct_NC_3 AS
SELECT *,
  CASE WHEN PL_MAX_AFFL <= PL_min_AFFL THEN PL_min_AFFL ELSE PL_MAX_AFFL END AS PL_MAX_AFFL1,
  CASE WHEN AL_MAX_AFFL <= Al_min_AFFL THEN Al_min_AFFL ELSE AL_MAX_AFFL END AS AL_MAX_AFFL1,
  CASE WHEN CC_CL_max_AFFL_n <= CC_CL_min_AFFL THEN CC_CL_min_AFFL ELSE CC_CL_max_AFFL_n END AS CC_CL_MAX_AFFL1,
  CASE WHEN CC_HCA_max_AFFL_n <= CC_HCA_min_AFFL THEN CC_HCA_min_AFFL ELSE CC_HCA_max_AFFL_n END AS CC_HCA_MAX_AFFL1,
  CASE WHEN HL_MAX_AFFL <= HL_min_AFFL THEN HL_min_AFFL ELSE HL_MAX_AFFL END AS HL_MAX_AFFL1,
  CASE WHEN LAP_MAX_AFFL <= LAP_min_AFFL THEN LAP_min_AFFL ELSE LAP_MAX_AFFL END AS LAP_MAX_AFFL1,
  EXTRACT(YEAR FROM DATE_OPENED) AS LOAN_YR
FROM sc_CIBIL_Aff_oct_NC_2;

-- ========== CELL 20: inflation index table ("YEAR"/"INDEX" quoted for DuckDB) ==========
DROP TABLE IF EXISTS SC_INFLATIONF_NC;
CREATE TABLE SC_INFLATIONF_NC ("YEAR" INT, "INDEX" INT);
INSERT INTO SC_INFLATIONF_NC ("YEAR", "INDEX") VALUES
    (2001, 100),(2002, 105),(2003, 109),(2004, 113),(2005, 117),(2006, 122),
    (2007, 129),(2008, 137),(2009, 148),(2010, 167),(2011, 184),(2012, 200),
    (2013, 220),(2014, 240),(2015, 254),(2016, 264),(2017, 272),(2018, 280),
    (2019, 289),(2020, 301),(2021, 317),(2022, 331),(2023, 348),(2024, 363),
    (2025, 376),(2026, 376);

-- ========== CELL 21: join inflation index on LOAN_YR ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC_4;
CREATE TABLE sc_CIBIL_Aff_oct_NC_4 AS
SELECT A.*, B."INDEX"
FROM sc_CIBIL_Aff_oct_NC_3 AS A
LEFT JOIN SC_INFLATIONF_NC AS B ON A.LOAN_YR = B."YEAR";

-- ========== CELL 22: inflation adjustment (* 376.0 / INDEX) ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC_5;
CREATE TABLE sc_CIBIL_Aff_oct_NC_5 AS
SELECT *,
  CASE WHEN "INDEX" >= 100 THEN AL_MAX_AFFL1 * 376.0 / "INDEX" ELSE AL_MAX_AFFL1 END AS AL_MAX_AFFL_N_1,
  CASE WHEN "INDEX" >= 100 THEN HL_MAX_AFFL1 * 376.0 / "INDEX" ELSE HL_MAX_AFFL1 END AS HL_MAX_AFFL_N_1,
  CASE WHEN "INDEX" >= 100 THEN PL_MAX_AFFL1 * 376.0 / "INDEX" ELSE PL_MAX_AFFL1 END AS PL_MAX_AFFL_N_1,
  CASE WHEN "INDEX" >= 100 THEN LAP_MAX_AFFL1 * 376.0 / "INDEX" ELSE LAP_MAX_AFFL1 END AS LAP_MAX_AFFL_N_1,
  CASE WHEN "INDEX" >= 100 THEN BL_MAX_AFFL * 376.0 / "INDEX" ELSE BL_MAX_AFFL END AS BL_MAX_AFFL_N_1,
  CASE WHEN "INDEX" >= 100 THEN CVCE_MAX_AFFL * 376.0 / "INDEX" ELSE CVCE_MAX_AFFL END AS CVCE_MAX_AFFL_1
FROM sc_CIBIL_Aff_oct_NC_4;

-- ========== CELL 23: per-CRN max of inflation-adjusted affluence + SA aggregates ==========
DROP TABLE IF EXISTS sc_CIBIL_Aff_oct_NC_6;
CREATE TABLE sc_CIBIL_Aff_oct_NC_6 AS
SELECT crn,
MAX(CC_CL_MAX_AFFL1) AS Max_CC_cl,
MAX(CC_HCA_MAX_AFFL1) AS Max_CC_HCA,
MAX(AL_MAX_AFFL_N_1) AS Max_AL,
MAX(HL_MAX_AFFL_N_1) AS Max_HL,
MAX(LAP_MAX_AFFL_N_1) AS Max_LAP,
MAX(BL_MAX_AFFL_N_1) AS Max_BL,
MAX(PL_MAX_AFFL_N_1) AS Max_PL,
MAX(CVCE_MAX_AFFL_1) AS Max_CVCE,
MAX(LTP_MAX_AFFL) AS Max_LTP,
MIN(CASE WHEN CC_CL_MAX_AFFL1 > 0 OR CC_HCA_MAX_AFFL1 > 0 THEN DATE_OPENED END) AS CC_DATE_OPEN,
max(case when loan_type_new in ('Auto Loan (Personal)','Used Car Loan') and tl_max_dpd < 30 then Sanction_Amount_new else 0 end) as max_AL_SA,
sum(case when loan_type_new in ('Auto Loan (Personal)','Used Car Loan') and tl_max_dpd < 30 then 1 else 0 end) as Count_AL,
max(case when loan_type_new in ('Housing Loan') and tl_max_dpd < 30 then Sanction_Amount_new else 0 end) as max_HL_SA,
max(case when bl_flag = 1 and tl_max_dpd < 30 then Sanction_Amount_new else 0 end) as max_bl_SA,
max(case when loan_type_new = 'Loan to Professional' and tl_max_dpd < 30 then Sanction_Amount_new else 0 end) as max_LTP_SA,
max(case when loan_type_new = 'Credit Card' and tl_max_dpd < 30 then COALESCE(creditlimit,High_Credit_Amount,Sanction_Amount_new) else 0 end) as max_CC,
max(case when loan_type_new in ('Personal Loan','Short Term Personal Loan','P2P Personal Loan','Microfinance - Personal Loan') and tl_max_dpd < 30 then Sanction_Amount_new else 0 end) as max_PL_SA
FROM sc_CIBIL_Aff_oct_NC_5
GROUP BY crn;

-- ========== CELL 25: occupation join + large-loan flags ==========
DROP TABLE IF EXISTS sc_bu_Affluence;
CREATE TABLE sc_bu_Affluence AS
SELECT a.*
,b.occupation AS occupation
,CASE WHEN a.max_bl_sa > 500000 THEN 1 ELSE 0 END AS flag_bl_large
,CASE WHEN a.max_pl_sa > 500000 THEN 1 ELSE 0 END AS flag_pl_large
,CASE WHEN a.max_ltp_sa > 500000 THEN 1 ELSE 0 END AS flag_ltp_large
,CASE WHEN a.max_hl_sa > 3000000 THEN 1 ELSE 0 END AS flag_hl_large
,CASE WHEN a.max_cc > 200000 THEN 1 ELSE 0 END AS flag_cc_large
FROM sc_CIBIL_Aff_oct_NC_6 a
LEFT JOIN occupation_input b ON a.crn = b.crn;

-- ========== CELL 27: SEMP flag, self-employed zeroing, AL adjust, MAX_AFFL7 waterfall ==========
DROP TABLE IF EXISTS sc_bu_Affluence1;
CREATE TABLE sc_bu_Affluence1 AS
SELECT *,
  CASE WHEN occupation IN ('S', 'SPRS', 'SGC', 'SPC') THEN 1 ELSE 0 END AS SEMP_flag1,
  CASE WHEN occupation IN ('S', 'SPRS', 'SGC', 'SPC') THEN 0 ELSE Max_BL END AS Max_BL1,
  CASE WHEN occupation IN ('S', 'SPRS', 'SGC', 'SPC') THEN 0 ELSE Max_LAP END AS Max_LAP1,
  CASE
      WHEN Max_AL > 0 THEN
          CASE
            WHEN flag_bl_large+flag_pl_large+flag_ltp_large+flag_hl_large+flag_cc_large = 0 THEN
              CASE
                WHEN max_AL_SA < 1500000 THEN LEAST(Max_AL / 2, 25000)
                WHEN max_AL_SA >= 1500000 AND COUNT_AL > 2 THEN LEAST(Max_AL / 2, 50000)
                ELSE Max_AL
              END
            ELSE Max_AL
          END
      ELSE 0
  END AS Max_AL1,
  CASE
    WHEN Max_HL > 0 THEN Max_HL
    WHEN Max_AL > 0 THEN Max_AL1
    WHEN Max_PL > 0 THEN Max_PL
    WHEN Max_BL1 > 0 THEN Max_BL1
    WHEN Max_LAP1 > 0 THEN Max_LAP1
    WHEN Max_CC_cl > 0 THEN Max_CC_cl
    WHEN Max_CC_HCA > 0 THEN Max_CC_HCA
    WHEN Max_CVCE > 0 THEN Max_CVCE
    ELSE 0
  END AS MAX_AFFL7
  ,greatest(Max_HL,Max_AL,Max_PL,Max_BL,Max_LAP,Max_CC_cl,Max_CC_HCA,Max_CVCE) AS max_bureau_income
FROM sc_bu_Affluence;

-- ========== CELL 28: final bureau income + stamp loan ==========
DROP TABLE IF EXISTS sc_bu_Affluence2;
CREATE TABLE sc_bu_Affluence2 AS
SELECT *,
  GREATEST(MAX_AFFL7, Max_LTP) AS MAX_AFFL_INFL_ROLL,
  1 AS CALCULATED_FLAG,
  CASE
    WHEN MAX_AFFL7 = 0 THEN 'NA'
    WHEN MAX_AFFL7 = Max_HL THEN 'Housing Loan'
    WHEN MAX_AFFL7 = Max_AL1 THEN 'Auto Loan'
    WHEN MAX_AFFL7 = Max_PL THEN 'Personal Loan'
    WHEN MAX_AFFL7 = Max_BL1 THEN 'Business Loan'
    WHEN MAX_AFFL7 = Max_LAP1 THEN 'Property Loan'
    WHEN MAX_AFFL7 = Max_CC_cl THEN 'Credit Card'
    WHEN MAX_AFFL7 = Max_CC_HCA THEN 'Credit Card -HCA'
    WHEN MAX_AFFL7 = Max_CVCE THEN 'CV CE'
    ELSE 'NA'
  END AS STAMP_LOAN
FROM sc_bu_Affluence1;
