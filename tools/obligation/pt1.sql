DECLARE
    v_etl_end_date VARCHAR(20);
	v_sql VARCHAR(65000);
	v_slc1 VARCHAR(20);
	v_slc2 VARCHAR(20);
	v_slc3 VARCHAR(20);
	v_slc4 VARCHAR(20);
	v_slc5 VARCHAR(20);
	v_slc6 VARCHAR(20);
	v_slc7 VARCHAR(20);
	v_slc8 VARCHAR(20);
	v_slc9 VARCHAR(20);
	v_slc10 VARCHAR(20);
	v_slc11 VARCHAR(20);
	v_slc12 VARCHAR(20);
	v_slc13 VARCHAR(20);

BEGIN 

-- Calculate last day of the month and convert to string
v_etl_end_date := TO_CHAR(LAST_DAY(etl_date::date), 'YYYY-MM-DD');

v_slc1 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -1), 'YYYYMM');
v_slc2 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -2), 'YYYYMM');
v_slc3 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -3), 'YYYYMM');
v_slc4 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -4), 'YYYYMM');
v_slc5 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -5), 'YYYYMM');
v_slc6 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -6), 'YYYYMM');
v_slc7 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -7), 'YYYYMM');
v_slc8 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -8), 'YYYYMM');
v_slc9 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -9), 'YYYYMM');
v_slc10 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -10), 'YYYYMM');
v_slc11 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -11), 'YYYYMM');
v_slc12 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -12), 'YYYYMM');
v_slc13 := to_char(ADD_MONTHS(v_etl_end_date::DATE, -13), 'YYYYMM');

DROP TABLE IF EXISTS t_SLC_data;

-- Step 1: Aggregate salary data by CRN and MONTH_ID
    v_sql := 'CREATE TEMP TABLE t_slc_data diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    MAX(CASE WHEN month_id = ' || v_slc1  || ' THEN salary ELSE 0 END) AS slc_' || v_slc1  || ',
    MAX(CASE WHEN month_id = ' || v_slc2  || ' THEN salary ELSE 0 END) AS slc_' || v_slc2  || ',
    MAX(CASE WHEN month_id = ' || v_slc3  || ' THEN salary ELSE 0 END) AS slc_' || v_slc3  || ',
    MAX(CASE WHEN month_id = ' || v_slc4  || ' THEN salary ELSE 0 END) AS slc_' || v_slc4  || ',
    MAX(CASE WHEN month_id = ' || v_slc5  || ' THEN salary ELSE 0 END) AS slc_' || v_slc5  || ',
    MAX(CASE WHEN month_id = ' || v_slc6  || ' THEN salary ELSE 0 END) AS slc_' || v_slc6  || ',
    MAX(CASE WHEN month_id = ' || v_slc7  || ' THEN salary ELSE 0 END) AS slc_' || v_slc7  || ',
    MAX(CASE WHEN month_id = ' || v_slc8  || ' THEN salary ELSE 0 END) AS slc_' || v_slc8  || ',
    MAX(CASE WHEN month_id = ' || v_slc9  || ' THEN salary ELSE 0 END) AS slc_' || v_slc9  || ',
    MAX(CASE WHEN month_id = ' || v_slc10 || ' THEN salary ELSE 0 END) AS slc_' || v_slc10 || ',
    MAX(CASE WHEN month_id = ' || v_slc11 || ' THEN salary ELSE 0 END) AS slc_' || v_slc11 || ',
    MAX(CASE WHEN month_id = ' || v_slc12 || ' THEN salary ELSE 0 END) AS slc_' || v_slc12 || ',
    MAX(CASE WHEN month_id = ' || v_slc13 || ' THEN salary ELSE 0 END) AS slc_' || v_slc13 || '
FROM
    KMBL_DEX.DMRT_VW.DM_CORPORATE_SALARY_HISTORY
WHERE
    "SNAPSHOT" = ''22-21''
    AND segment IN (''SEGMENT_A_RISK_PRODUCT'',''SEGMENT_B_RISK_PRODUCT'')
GROUP BY
    crn';

    -- Optional: print generated SQL for debugging
    -- RAISE INFO '%', v_sql;

EXECUTE v_sql;

analyze t_SLC_data;

DROP TABLE IF EXISTS t_SLC1;
-- Step 2: Apply conditional logic to derive _R columns
-- Build t_SLC1 with dynamic _R columns
v_sql := 'CREATE TEMP TABLE t_SLC1 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc1 || ' ELSE slc_' || v_slc2  || ' END AS slc_' || v_slc1  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc2 || ' ELSE slc_' || v_slc3  || ' END AS slc_' || v_slc2  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc3 || ' ELSE slc_' || v_slc4  || ' END AS slc_' || v_slc3  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc4 || ' ELSE slc_' || v_slc5  || ' END AS slc_' || v_slc4  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc5 || ' ELSE slc_' || v_slc6  || ' END AS slc_' || v_slc5  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc6 || ' ELSE slc_' || v_slc7  || ' END AS slc_' || v_slc6  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc7 || ' ELSE slc_' || v_slc8  || ' END AS slc_' || v_slc7  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc8 || ' ELSE slc_' || v_slc9  || ' END AS slc_' || v_slc8  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc9 || ' ELSE slc_' || v_slc10 || ' END AS slc_' || v_slc9  || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc10|| ' ELSE slc_' || v_slc11 || ' END AS slc_' || v_slc10 || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc11|| ' ELSE slc_' || v_slc12 || ' END AS slc_' || v_slc11 || '_r,
    CASE WHEN slc_' || v_slc1 || ' > 0 THEN slc_' || v_slc12|| ' ELSE slc_' || v_slc13 || ' END AS slc_' || v_slc12 || '_r
FROM t_slc_data';
                                                            

EXECUTE v_sql;
analyze t_SLC1;

DROP TABLE IF EXISTS t_SLC_last6m;

v_sql := 'CREATE TEMP TABLE t_slc_last6m diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc1  || '_r ELSE NULL END AS slc_' || v_slc1  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc2  || '_r ELSE NULL END AS slc_' || v_slc2  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc3  || '_r ELSE NULL END AS slc_' || v_slc3  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc4  || '_r ELSE NULL END AS slc_' || v_slc4  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc5  || '_r ELSE NULL END AS slc_' || v_slc5  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc6  || '_r ELSE NULL END AS slc_' || v_slc6  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc7  || '_r ELSE NULL END AS slc_' || v_slc7  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc8  || '_r ELSE NULL END AS slc_' || v_slc8  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc9  || '_r ELSE NULL END AS slc_' || v_slc9  || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc10 || '_r ELSE NULL END AS slc_' || v_slc10 || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc11 || '_r ELSE NULL END AS slc_' || v_slc11 || ',
    CASE WHEN TRIM(crn) <> '''' THEN slc_' || v_slc12 || '_r ELSE NULL END AS slc_' || v_slc12 || '
FROM t_slc1
WHERE TRIM(crn) <> ''''
  AND crn IS NOT NULL';

EXECUTE v_sql;
analyze t_SLC_last6m;

DROP TABLE IF EXISTS t_LOS_INCOME_WITH_YEAR;

CREATE TEMP TABLE t_LOS_INCOME_WITH_YEAR diststyle key distkey(crn) sortkey(crn) AS
SELECT
    a.crn,
    a.Accnt_Opn_Date,
    DATE_PART('year', ADD_MONTHS(v_etl_end_date::DATE, -1)) - DATE_PART('year', a.Accnt_Opn_Date) AS SAL_AGE,
    ROUND(
        CASE
            WHEN MAX(a.los_income) IS NULL THEN 0
            ELSE MAX(a.los_income)
        END
    ) AS LOS_INCOME,
    EXTRACT(
        YEAR
        FROM
            a.Accnt_Opn_Date
    ) AS year
FROM kmbl_ra.bba_ra_papq.risk_los_income a
-- (SELECT * FROM kmbl_risk.sandbox.los_income_final where business_month=to_char(v_etl_end_date::DATE,'YYYYMM')::int) a
    JOIN (
        SELECT
            crn,
            MAX(Accnt_Opn_Date) AS MAX_DT
        FROM kmbl_ra.bba_ra_papq.risk_los_income
       -- kmbl_risk.sandbox.los_income_final 
      -- WHERE business_month=to_char(v_etl_end_date::DATE,'YYYYMM')::int
        GROUP BY
            crn
    ) b ON a.crn = b.crn
    AND a.Accnt_Opn_Date = b.MAX_DT
WHERE
    nvl(UPPER(CAST(a.los_income AS VARCHAR)),'x') <> 'OWNED'
    AND a.crn NOT IN (0, 1)
    AND a.crn IS NOT NULL
GROUP BY
    a.crn,
    a.Accnt_Opn_Date;
	
analyze t_LOS_INCOME_WITH_YEAR;

DROP TABLE IF EXISTS t_los_income_2;

CREATE TEMP TABLE t_los_income_2 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    A.*,
    B.inf_index_value AS INDEX,
    CASE
        WHEN B.inf_index_value >= 100 THEN ROUND( (A.LOS_INCOME * 363.0)::decimal / B.inf_index_value, 2)
        ELSE NULL
    END AS LOS_INCOME_AFF
FROM
    t_LOS_INCOME_WITH_YEAR A
    LEFT JOIN kmbl_ra.bba_ra_papq.risk_inflation_index B ON A.year = B.year_val;
	
analyze t_los_income_2;

DROP TABLE IF EXISTS t_SLC_5YR_Dt_v1;

v_sql := 'CREATE TEMP TABLE t_slc_5yr_dt_v1 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    a.*,
    b.slc_' || v_slc1  || '  AS b_slc_' || v_slc1  || ',
    b.slc_' || v_slc2  || '  AS b_slc_' || v_slc2  || ',
    b.slc_' || v_slc3  || '  AS b_slc_' || v_slc3  || ',
    b.slc_' || v_slc4  || '  AS b_slc_' || v_slc4  || ',
    b.slc_' || v_slc5  || '  AS b_slc_' || v_slc5  || ',
    b.slc_' || v_slc6  || '  AS b_slc_' || v_slc6  || ',
    b.slc_' || v_slc7  || '  AS b_slc_' || v_slc7  || ',
    b.slc_' || v_slc8  || '  AS b_slc_' || v_slc8  || ',
    b.slc_' || v_slc9  || '  AS b_slc_' || v_slc9  || ',
    b.slc_' || v_slc10 || ' AS b_slc_' || v_slc10 || '
FROM
    kmbl_ra.bba_ra_papq.risk_slc_data a
    LEFT JOIN t_slc_last6m b ON a.crn = b.crn';


EXECUTE v_sql;
analyze t_SLC_5YR_Dt_v1;


DROP TABLE IF EXISTS t_slc_5yr_unpivoted;

v_sql := 'CREATE TEMP TABLE t_slc_5yr_unpivoted diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    ''SLC_' || v_slc1 || ''' AS column_name,
    b_slc_' || v_slc1 || ' AS salary
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc2 || ''' ,
    b_slc_' || v_slc2 || ' 
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc3 || ''' ,
    b_slc_' || v_slc3 || ' 
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc4 || ''' ,
    b_slc_' || v_slc4 || ' 
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc5 || ''' ,
    b_slc_' || v_slc5 || ' 
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc6 || ''',
    b_slc_' || v_slc6 || ' 
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc7 || ''',
    b_slc_' || v_slc7 || ' 
FROM t_slc_5yr_dt_v1
UNION ALL
SELECT
    crn,
    ''SLC_' || v_slc8 || ''',
    b_slc_' || v_slc8 || '
FROM t_slc_5yr_dt_v1
union all
SELECT
    crn,
    ''SLC_202504'',
    SLC_202504
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202503'',
    SLC_202503
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202502'',
    SLC_202502
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202501'',
    SLC_202501
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202412'',
    SLC_202412
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202411'',
    SLC_202411
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202410'',
    SLC_202410
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202409'',
    SLC_202409
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202408'',
    SLC_202408
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202407'',
    SLC_202407
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202406'',
    SLC_202406
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202405'',
    SLC_202405
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202404'',
    SLC_202404
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202403'',
    SLC_202403
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202402'',
    slc_202402
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202401'',
    slc_202401
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202312'',
    slc_202312
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202311'',
    slc_202311
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202310'',
    slc_202310
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202309'',
    slc_202309
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202308'',
    slc_202308
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202307'',
    slc_202307
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202306'',
    slc_202306
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202305'',
    slc_202305
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202304'',
    slc_202304
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202303'',
    slc_202303
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202302'',
    slc_202302
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202301'',
    slc_202301
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202212'',
    slc_202212
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202211'',
    slc_202211
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202210'',
    slc_202210
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202209'',
    slc_202209
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202208'',
    slc_202208
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202207'',
    slc_202207
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202206'',
    slc_202206
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202205'',
    slc_202205
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202204'',
    slc_202204
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202203'',
    slc_202203
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202202'',
    slc_202202
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202201'',
    slc_202201
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202112'',
    slc_202112
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202111'',
    slc_202111
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202110'',
    slc_202110
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202109'',
    slc_202109
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202108'',
    slc_202108
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202107'',
    slc_202107
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202106'',
    slc_202106
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202105'',
    slc_202105
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202104'',
    slc_202104
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202103'',
    slc_202103
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202102'',
    slc_202102
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202101'',
    slc_202101
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202012'',
    slc_202012
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202011'',
    slc_202011
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202010'',
    slc_202010
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''slc_202009'',
    slc_202009
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202008'',
    SLC_202008
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202007'',
    SLC_202007
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202006'',
    SLC_202006
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202005'',
    SLC_202005
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202004'',
    SLC_202004
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202003'',
    SLC_202003
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202002'',
    SLC_202002
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_202001'',
    SLC_202001
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201912'',
    SLC_201912
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201911'',
    SLC_201911
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201910'',
    SLC_201910
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201909'',
    SLC_201909
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201908'',
    SLC_201908
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201907'',
    SLC_201907
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201906'',
    SLC_201906
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201905'',
    SLC_201905
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201904'',
    SLC_201904
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201903'',
    SLC_201903
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201902'',
    SLC_201902
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201901'',
    SLC_201901
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201812'',
    SLC_201812
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201811'',
    SLC_201811
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201810'',
    SLC_201810
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201809'',
    SLC_201809
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201808'',
    SLC_201808
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201807'',
    SLC_201807
FROM
    t_SLC_5YR_Dt_v1
	union all
SELECT
    crn,
    ''SLC_201806'',
    SLC_201806
FROM
    t_SLC_5YR_Dt_v1
union all
SELECT
    crn,
    ''SLC_201805'',
    SLC_201805
FROM
    t_SLC_5YR_Dt_v1';

EXECUTE v_sql;
analyze t_slc_5yr_unpivoted;

DROP TABLE IF EXISTS t_SAL_ever_sol;

CREATE TEMP TABLE t_SAL_ever_sol diststyle key distkey(crn) sortkey(crn) AS
SELECT
    *
FROM
    (
        SELECT
            *,
            TO_DATE(
                LPAD(SUBSTRING(Column_name, 9, 2), 2, '0') || '-01-' || SUBSTRING(Column_name, 5, 4),
                'MM-DD-YYYY'
            ) AS salary_date,
            RANK() OVER (
                PARTITION BY crn
                ORDER BY
                    TO_DATE(
                        LPAD(SUBSTRING(Column_name, 9, 2), 2, '0') || '-01-' || SUBSTRING(Column_name, 5, 4),
                        'MM-DD-YYYY'
                    ) DESC
            ) AS rank
        FROM
            t_slc_5yr_unpivoted
    ) ranked_data
WHERE
    rank <= 60
ORDER BY
    crn,
    rank;

analyze t_SAL_ever_sol;

DROP TABLE IF EXISTS t_SAL_ever_sol_1;

CREATE TEMP TABLE t_SAL_ever_sol_1 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    MAX(
        CASE
            WHEN rank = 1 THEN salary
            ELSE NULL
        END
    ) AS month_1,
    MAX(
        CASE
            WHEN rank = 2 THEN salary
            ELSE NULL
        END
    ) AS month_2,
    MAX(
        CASE
            WHEN rank = 3 THEN salary
            ELSE NULL
        END
    ) AS month_3,
    MAX(
        CASE
            WHEN rank = 4 THEN salary
            ELSE NULL
        END
    ) AS month_4,
    MAX(
        CASE
            WHEN rank = 5 THEN salary
            ELSE NULL
        END
    ) AS month_5,
    MAX(
        CASE
            WHEN rank = 6 THEN salary
            ELSE NULL
        END
    ) AS month_6,
    MAX(
        CASE
            WHEN rank = 7 THEN salary
            ELSE NULL
        END
    ) AS month_7,
    MAX(
        CASE
            WHEN rank = 8 THEN salary
            ELSE NULL
        END
    ) AS month_8,
    MAX(
        CASE
            WHEN rank = 9 THEN salary
            ELSE NULL
        END
    ) AS month_9,
    MAX(
        CASE
            WHEN rank = 10 THEN salary
            ELSE NULL
        END
    ) AS month_10,
    MAX(
        CASE
            WHEN rank = 11 THEN salary
            ELSE NULL
        END
    ) AS month_11,
    MAX(
        CASE
            WHEN rank = 12 THEN salary
            ELSE NULL
        END
    ) AS month_12,
    MAX(
        CASE
            WHEN rank = 13 THEN salary
            ELSE NULL
        END
    ) AS month_13,
    MAX(
        CASE
            WHEN rank = 14 THEN salary
            ELSE NULL
        END
    ) AS month_14,
    MAX(
        CASE
            WHEN rank = 15 THEN salary
            ELSE NULL
        END
    ) AS month_15,
    MAX(
        CASE
            WHEN rank = 16 THEN salary
            ELSE NULL
        END
    ) AS month_16,
    MAX(
        CASE
            WHEN rank = 17 THEN salary
            ELSE NULL
        END
    ) AS month_17,
    MAX(
        CASE
            WHEN rank = 18 THEN salary
            ELSE NULL
        END
    ) AS month_18,
    MAX(
        CASE
            WHEN rank = 19 THEN salary
            ELSE NULL
        END
    ) AS month_19,
    MAX(
        CASE
            WHEN rank = 20 THEN salary
            ELSE NULL
        END
    ) AS month_20,
    MAX(
        CASE
            WHEN rank = 21 THEN salary
            ELSE NULL
        END
    ) AS month_21,
    MAX(
        CASE
            WHEN rank = 22 THEN salary
            ELSE NULL
        END
    ) AS month_22,
    MAX(
        CASE
            WHEN rank = 23 THEN salary
            ELSE NULL
        END
    ) AS month_23,
    MAX(
        CASE
            WHEN rank = 24 THEN salary
            ELSE NULL
        END
    ) AS month_24,
    MAX(
        CASE
            WHEN rank = 25 THEN salary
            ELSE NULL
        END
    ) AS month_25,
    MAX(
        CASE
            WHEN rank = 26 THEN salary
            ELSE NULL
        END
    ) AS month_26,
    MAX(
        CASE
            WHEN rank = 27 THEN salary
            ELSE NULL
        END
    ) AS month_27,
    MAX(
        CASE
            WHEN rank = 28 THEN salary
            ELSE NULL
        END
    ) AS month_28,
    MAX(
        CASE
            WHEN rank = 29 THEN salary
            ELSE NULL
        END
    ) AS month_29,
    MAX(
        CASE
            WHEN rank = 30 THEN salary
            ELSE NULL
        END
    ) AS month_30,
    MAX(
        CASE
            WHEN rank = 31 THEN salary
            ELSE NULL
        END
    ) AS month_31,
    MAX(
        CASE
            WHEN rank = 32 THEN salary
            ELSE NULL
        END
    ) AS month_32,
    MAX(
        CASE
            WHEN rank = 33 THEN salary
            ELSE NULL
        END
    ) AS month_33,
    MAX(
        CASE
            WHEN rank = 34 THEN salary
            ELSE NULL
        END
    ) AS month_34,
    MAX(
        CASE
            WHEN rank = 35 THEN salary
            ELSE NULL
        END
    ) AS month_35,
    MAX(
        CASE
            WHEN rank = 36 THEN salary
            ELSE NULL
        END
    ) AS month_36,
    MAX(
        CASE
            WHEN rank = 37 THEN salary
            ELSE NULL
        END
    ) AS month_37,
    MAX(
        CASE
            WHEN rank = 38 THEN salary
            ELSE NULL
        END
    ) AS month_38,
    MAX(
        CASE
            WHEN rank = 39 THEN salary
            ELSE NULL
        END
    ) AS month_39,
    MAX(
        CASE
            WHEN rank = 40 THEN salary
            ELSE NULL
        END
    ) AS month_40,
    MAX(
        CASE
            WHEN rank = 41 THEN salary
            ELSE NULL
        END
    ) AS month_41,
    MAX(
        CASE
            WHEN rank = 42 THEN salary
            ELSE NULL
        END
    ) AS month_42,
    MAX(
        CASE
            WHEN rank = 43 THEN salary
            ELSE NULL
        END
    ) AS month_43,
    MAX(
        CASE
            WHEN rank = 44 THEN salary
            ELSE NULL
        END
    ) AS month_44,
    MAX(
        CASE
            WHEN rank = 45 THEN salary
            ELSE NULL
        END
    ) AS month_45,
    MAX(
        CASE
            WHEN rank = 46 THEN salary
            ELSE NULL
        END
    ) AS month_46,
    MAX(
        CASE
            WHEN rank = 47 THEN salary
            ELSE NULL
        END
    ) AS month_47,
    MAX(
        CASE
            WHEN rank = 48 THEN salary
            ELSE NULL
        END
    ) AS month_48,
    MAX(
        CASE
            WHEN rank = 49 THEN salary
            ELSE NULL
        END
    ) AS month_49,
    MAX(
        CASE
            WHEN rank = 50 THEN salary
            ELSE NULL
        END
    ) AS month_50,
    MAX(
        CASE
            WHEN rank = 51 THEN salary
            ELSE NULL
        END
    ) AS month_51,
    MAX(
        CASE
            WHEN rank = 52 THEN salary
            ELSE NULL
        END
    ) AS month_52,
    MAX(
        CASE
            WHEN rank = 53 THEN salary
            ELSE NULL
        END
    ) AS month_53,
    MAX(
        CASE
            WHEN rank = 54 THEN salary
            ELSE NULL
        END
    ) AS month_54,
    MAX(
        CASE
            WHEN rank = 55 THEN salary
            ELSE NULL
        END
    ) AS month_55,
    MAX(
        CASE
            WHEN rank = 56 THEN salary
            ELSE NULL
        END
    ) AS month_56,
    MAX(
        CASE
            WHEN rank = 57 THEN salary
            ELSE NULL
        END
    ) AS month_57,
    MAX(
        CASE
            WHEN rank = 58 THEN salary
            ELSE NULL
        END
    ) AS month_58,
    MAX(
        CASE
            WHEN rank = 59 THEN salary
            ELSE NULL
        END
    ) AS month_59,
    MAX(
        CASE
            WHEN rank = 60 THEN salary
            ELSE NULL
        END
    ) AS month_60,
    CASE
        WHEN month_1 > 0
        AND month_2 > 0
        AND month_3 > 0 THEN LEAST(month_1, month_2, month_3)
        WHEN month_2 > 0
        AND month_3 > 0
        AND month_4 > 0 THEN LEAST(month_2, month_3, month_4)
        WHEN month_3 > 0
        AND month_4 > 0
        AND month_5 > 0 THEN LEAST(month_3, month_4, month_5)
        WHEN month_4 > 0
        AND month_5 > 0
        AND month_6 > 0 THEN LEAST(month_4, month_5, month_6)
        WHEN month_5 > 0
        AND month_6 > 0
        AND month_7 > 0 THEN LEAST(month_5, month_6, month_7)
        WHEN month_6 > 0
        AND month_7 > 0
        AND month_8 > 0 THEN LEAST(month_6, month_7, month_8)
        WHEN month_7 > 0
        AND month_8 > 0
        AND month_9 > 0 THEN LEAST(month_7, month_8, month_9)
        WHEN month_8 > 0
        AND month_9 > 0
        AND month_10 > 0 THEN LEAST(month_8, month_9, month_10)
        WHEN month_9 > 0
        AND month_10 > 0
        AND month_11 > 0 THEN LEAST(month_9, month_10, month_11)
        WHEN month_10 > 0
        AND month_11 > 0
        AND month_12 > 0 THEN LEAST(month_10, month_11, month_12)
        WHEN month_11 > 0
        AND month_12 > 0
        AND month_13 > 0 THEN LEAST(month_11, month_12, month_13)
        WHEN month_12 > 0
        AND month_13 > 0
        AND month_14 > 0 THEN LEAST(month_12, month_13, month_14)
        WHEN month_13 > 0
        AND month_14 > 0
        AND month_15 > 0 THEN LEAST(month_13, month_14, month_15)
        WHEN month_14 > 0
        AND month_15 > 0
        AND month_16 > 0 THEN LEAST(month_14, month_15, month_16)
        WHEN month_15 > 0
        AND month_16 > 0
        AND month_17 > 0 THEN LEAST(month_15, month_16, month_17)
        WHEN month_16 > 0
        AND month_17 > 0
        AND month_18 > 0 THEN LEAST(month_16, month_17, month_18)
        WHEN month_17 > 0
        AND month_18 > 0
        AND month_19 > 0 THEN LEAST(month_17, month_18, month_19)
        WHEN month_18 > 0
        AND month_19 > 0
        AND month_20 > 0 THEN LEAST(month_18, month_19, month_20)
        WHEN month_19 > 0
        AND month_20 > 0
        AND month_21 > 0 THEN LEAST(month_19, month_20, month_21)
        WHEN month_20 > 0
        AND month_21 > 0
        AND month_22 > 0 THEN LEAST(month_20, month_21, month_22)
        WHEN month_21 > 0
        AND month_22 > 0
        AND month_23 > 0 THEN LEAST(month_21, month_22, month_23)
        WHEN month_22 > 0
        AND month_23 > 0
        AND month_24 > 0 THEN LEAST(month_22, month_23, month_24)
        WHEN month_23 > 0
        AND month_24 > 0
        AND month_25 > 0 THEN LEAST(month_23, month_24, month_25)
        WHEN month_24 > 0
        AND month_25 > 0
        AND month_26 > 0 THEN LEAST(month_24, month_25, month_26)
        WHEN month_25 > 0
        AND month_26 > 0
        AND month_27 > 0 THEN LEAST(month_25, month_26, month_27)
        WHEN month_26 > 0
        AND month_27 > 0
        AND month_28 > 0 THEN LEAST(month_26, month_27, month_28)
        WHEN month_27 > 0
        AND month_28 > 0
        AND month_29 > 0 THEN LEAST(month_27, month_28, month_29)
        WHEN month_28 > 0
        AND month_29 > 0
        AND month_30 > 0 THEN LEAST(month_28, month_29, month_30)
        WHEN month_29 > 0
        AND month_30 > 0
        AND month_31 > 0 THEN LEAST(month_29, month_30, month_31)
        WHEN month_30 > 0
        AND month_31 > 0
        AND month_32 > 0 THEN LEAST(month_30, month_31, month_32)
        WHEN month_31 > 0
        AND month_32 > 0
        AND month_33 > 0 THEN LEAST(month_31, month_32, month_33)
        WHEN month_32 > 0
        AND month_33 > 0
        AND month_34 > 0 THEN LEAST(month_32, month_33, month_34)
        WHEN month_33 > 0
        AND month_34 > 0
        AND month_35 > 0 THEN LEAST(month_33, month_34, month_35)
        WHEN month_34 > 0
        AND month_35 > 0
        AND month_36 > 0 THEN LEAST(month_34, month_35, month_36)
        WHEN month_35 > 0
        AND month_36 > 0
        AND month_37 > 0 THEN LEAST(month_35, month_36, month_37)
        WHEN month_36 > 0
        AND month_37 > 0
        AND month_38 > 0 THEN LEAST(month_36, month_37, month_38)
        WHEN month_37 > 0
        AND month_38 > 0
        AND month_39 > 0 THEN LEAST(month_37, month_38, month_39)
        WHEN month_38 > 0
        AND month_39 > 0
        AND month_40 > 0 THEN LEAST(month_38, month_39, month_40)
        WHEN month_39 > 0
        AND month_40 > 0
        AND month_41 > 0 THEN LEAST(month_39, month_40, month_41)
        WHEN month_40 > 0
        AND month_41 > 0
        AND month_42 > 0 THEN LEAST(month_40, month_41, month_42)
        WHEN month_41 > 0
        AND month_42 > 0
        AND month_43 > 0 THEN LEAST(month_41, month_42, month_43)
        WHEN month_42 > 0
        AND month_43 > 0
        AND month_44 > 0 THEN LEAST(month_42, month_43, month_44)
        WHEN month_43 > 0
        AND month_44 > 0
        AND month_45 > 0 THEN LEAST(month_43, month_44, month_45)
        WHEN month_44 > 0
        AND month_45 > 0
        AND month_46 > 0 THEN LEAST(month_44, month_45, month_46)
        WHEN month_45 > 0
        AND month_46 > 0
        AND month_47 > 0 THEN LEAST(month_45, month_46, month_47)
        WHEN month_46 > 0
        AND month_47 > 0
        AND month_48 > 0 THEN LEAST(month_46, month_47, month_48)
        WHEN month_47 > 0
        AND month_48 > 0
        AND month_49 > 0 THEN LEAST(month_47, month_48, month_49)
        WHEN month_48 > 0
        AND month_49 > 0
        AND month_50 > 0 THEN LEAST(month_48, month_49, month_50)
        WHEN month_49 > 0
        AND month_50 > 0
        AND month_51 > 0 THEN LEAST(month_49, month_50, month_51)
        WHEN month_50 > 0
        AND month_51 > 0
        AND month_52 > 0 THEN LEAST(month_50, month_51, month_52)
        WHEN month_51 > 0
        AND month_52 > 0
        AND month_53 > 0 THEN LEAST(month_51, month_52, month_53)
        WHEN month_52 > 0
        AND month_53 > 0
        AND month_54 > 0 THEN LEAST(month_52, month_53, month_54)
        WHEN month_53 > 0
        AND month_54 > 0
        AND month_55 > 0 THEN LEAST(month_53, month_54, month_55)
        WHEN month_54 > 0
        AND month_55 > 0
        AND month_56 > 0 THEN LEAST(month_54, month_55, month_56)
        WHEN month_55 > 0
        AND month_56 > 0
        AND month_57 > 0 THEN LEAST(month_55, month_56, month_57)
        WHEN month_56 > 0
        AND month_57 > 0
        AND month_58 > 0 THEN LEAST(month_56, month_57, month_58)
        WHEN month_57 > 0
        AND month_58 > 0
        AND month_59 > 0 THEN LEAST(month_57, month_58, month_59)
        WHEN month_58 > 0
        AND month_59 > 0
        AND month_60 > 0 THEN LEAST(month_58, month_59, month_60)
        ELSE NULL
    END AS salary,
    CASE
        WHEN month_1 > 0
        AND month_2 > 0
        AND month_3 > 0 THEN CASE
            WHEN month_1 = LEAST(month_1, month_2, month_3) THEN 1
            WHEN month_2 = LEAST(month_1, month_2, month_3) THEN 2
            ELSE 3
        END
        WHEN month_2 > 0
        AND month_3 > 0
        AND month_4 > 0 THEN CASE
            WHEN month_2 = LEAST(month_2, month_3, month_4) THEN 2
            WHEN month_3 = LEAST(month_2, month_3, month_4) THEN 3
            ELSE 4
        END
        WHEN month_3 > 0
        AND month_4 > 0
        AND month_5 > 0 THEN CASE
            WHEN month_3 = LEAST(month_3, month_4, month_5) THEN 3
            WHEN month_4 = LEAST(month_3, month_4, month_5) THEN 4
            ELSE 5
        END
        WHEN month_4 > 0
        AND month_5 > 0
        AND month_6 > 0 THEN CASE
            WHEN month_4 = LEAST(month_4, month_5, month_6) THEN 4
            WHEN month_5 = LEAST(month_4, month_5, month_6) THEN 5
            ELSE 6
        END
        WHEN month_5 > 0
        AND month_6 > 0
        AND month_7 > 0 THEN CASE
            WHEN month_5 = LEAST(month_5, month_6, month_7) THEN 5
            WHEN month_6 = LEAST(month_5, month_6, month_7) THEN 6
            ELSE 7
        END
        WHEN month_6 > 0
        AND month_7 > 0
        AND month_8 > 0 THEN CASE
            WHEN month_6 = LEAST(month_6, month_7, month_8) THEN 6
            WHEN month_7 = LEAST(month_6, month_7, month_8) THEN 7
            ELSE 8
        END
        WHEN month_7 > 0
        AND month_8 > 0
        AND month_9 > 0 THEN CASE
            WHEN month_7 = LEAST(month_7, month_8, month_9) THEN 7
            WHEN month_8 = LEAST(month_7, month_8, month_9) THEN 8
            ELSE 9
        END
        WHEN month_8 > 0
        AND month_9 > 0
        AND month_10 > 0 THEN CASE
            WHEN month_8 = LEAST(month_8, month_9, month_10) THEN 8
            WHEN month_9 = LEAST(month_8, month_9, month_10) THEN 9
            ELSE 10
        END
        WHEN month_9 > 0
        AND month_10 > 0
        AND month_11 > 0 THEN CASE
            WHEN month_9 = LEAST(month_9, month_10, month_11) THEN 9
            WHEN month_10 = LEAST(month_9, month_10, month_11) THEN 10
            ELSE 11
        END
        WHEN month_10 > 0
        AND month_11 > 0
        AND month_12 > 0 THEN CASE
            WHEN month_10 = LEAST(month_10, month_11, month_12) THEN 10
            WHEN month_11 = LEAST(month_10, month_11, month_12) THEN 11
            ELSE 12
        END
        WHEN month_11 > 0
        AND month_12 > 0
        AND month_13 > 0 THEN CASE
            WHEN month_11 = LEAST(month_11, month_12, month_13) THEN 11
            WHEN month_12 = LEAST(month_11, month_12, month_13) THEN 12
            ELSE 13
        END
        WHEN month_12 > 0
        AND month_13 > 0
        AND month_14 > 0 THEN CASE
            WHEN month_12 = LEAST(month_12, month_13, month_14) THEN 12
            WHEN month_13 = LEAST(month_12, month_13, month_14) THEN 13
            ELSE 14
        END
        WHEN month_13 > 0
        AND month_14 > 0
        AND month_15 > 0 THEN CASE
            WHEN month_13 = LEAST(month_13, month_14, month_15) THEN 13
            WHEN month_14 = LEAST(month_13, month_14, month_15) THEN 14
            ELSE 15
        END
        WHEN month_14 > 0
        AND month_15 > 0
        AND month_16 > 0 THEN CASE
            WHEN month_14 = LEAST(month_14, month_15, month_16) THEN 14
            WHEN month_15 = LEAST(month_14, month_15, month_16) THEN 15
            ELSE 16
        END
        WHEN month_15 > 0
        AND month_16 > 0
        AND month_17 > 0 THEN CASE
            WHEN month_15 = LEAST(month_15, month_16, month_17) THEN 15
            WHEN month_16 = LEAST(month_15, month_16, month_17) THEN 16
            ELSE 17
        END
        WHEN month_16 > 0
        AND month_17 > 0
        AND month_18 > 0 THEN CASE
            WHEN month_16 = LEAST(month_16, month_17, month_18) THEN 16
            WHEN month_17 = LEAST(month_16, month_17, month_18) THEN 17
            ELSE 18
        END
        WHEN month_17 > 0
        AND month_18 > 0
        AND month_19 > 0 THEN CASE
            WHEN month_17 = LEAST(month_17, month_18, month_19) THEN 17
            WHEN month_18 = LEAST(month_17, month_18, month_19) THEN 18
            ELSE 19
        END
        WHEN month_18 > 0
        AND month_19 > 0
        AND month_20 > 0 THEN CASE
            WHEN month_18 = LEAST(month_18, month_19, month_20) THEN 18
            WHEN month_19 = LEAST(month_18, month_19, month_20) THEN 19
            ELSE 20
        END
        WHEN month_19 > 0
        AND month_20 > 0
        AND month_21 > 0 THEN CASE
            WHEN month_19 = LEAST(month_19, month_20, month_21) THEN 19
            WHEN month_20 = LEAST(month_19, month_20, month_21) THEN 20
            ELSE 21
        END
        WHEN month_20 > 0
        AND month_21 > 0
        AND month_22 > 0 THEN CASE
            WHEN month_20 = LEAST(month_20, month_21, month_22) THEN 20
            WHEN month_21 = LEAST(month_20, month_21, month_22) THEN 21
            ELSE 22
        END
        WHEN month_21 > 0
        AND month_22 > 0
        AND month_23 > 0 THEN CASE
            WHEN month_21 = LEAST(month_21, month_22, month_23) THEN 21
            WHEN month_22 = LEAST(month_21, month_22, month_23) THEN 22
            ELSE 23
        END
        WHEN month_22 > 0
        AND month_23 > 0
        AND month_24 > 0 THEN CASE
            WHEN month_22 = LEAST(month_22, month_23, month_24) THEN 22
            WHEN month_23 = LEAST(month_22, month_23, month_24) THEN 23
            ELSE 24
        END
        WHEN month_23 > 0
        AND month_24 > 0
        AND month_25 > 0 THEN CASE
            WHEN month_23 = LEAST(month_23, month_24, month_25) THEN 23
            WHEN month_24 = LEAST(month_23, month_24, month_25) THEN 24
            ELSE 25
        END
        WHEN month_24 > 0
        AND month_25 > 0
        AND month_26 > 0 THEN CASE
            WHEN month_24 = LEAST(month_24, month_25, month_26) THEN 24
            WHEN month_25 = LEAST(month_24, month_25, month_26) THEN 25
            ELSE 26
        END
        WHEN month_25 > 0
        AND month_26 > 0
        AND month_27 > 0 THEN CASE
            WHEN month_25 = LEAST(month_25, month_26, month_27) THEN 25
            WHEN month_26 = LEAST(month_25, month_26, month_27) THEN 26
            ELSE 27
        END
        WHEN month_26 > 0
        AND month_27 > 0
        AND month_28 > 0 THEN CASE
            WHEN month_26 = LEAST(month_26, month_27, month_28) THEN 26
            WHEN month_27 = LEAST(month_26, month_27, month_28) THEN 27
            ELSE 28
        END
        WHEN month_27 > 0
        AND month_28 > 0
        AND month_29 > 0 THEN CASE
            WHEN month_27 = LEAST(month_27, month_28, month_29) THEN 27
            WHEN month_28 = LEAST(month_27, month_28, month_29) THEN 28
            ELSE 29
        END
        WHEN month_28 > 0
        AND month_29 > 0
        AND month_30 > 0 THEN CASE
            WHEN month_28 = LEAST(month_28, month_29, month_30) THEN 28
            WHEN month_29 = LEAST(month_28, month_29, month_30) THEN 29
            ELSE 30
        END
        WHEN month_29 > 0
        AND month_30 > 0
        AND month_31 > 0 THEN CASE
            WHEN month_29 = LEAST(month_29, month_30, month_31) THEN 29
            WHEN month_30 = LEAST(month_29, month_30, month_31) THEN 30
            ELSE 31
        END
        WHEN month_30 > 0
        AND month_31 > 0
        AND month_32 > 0 THEN CASE
            WHEN month_30 = LEAST(month_30, month_31, month_32) THEN 30
            WHEN month_31 = LEAST(month_30, month_31, month_32) THEN 31
            ELSE 32
        END
        WHEN month_31 > 0
        AND month_32 > 0
        AND month_33 > 0 THEN CASE
            WHEN month_31 = LEAST(month_31, month_32, month_33) THEN 31
            WHEN month_32 = LEAST(month_31, month_32, month_33) THEN 32
            ELSE 33
        END
        WHEN month_32 > 0
        AND month_33 > 0
        AND month_34 > 0 THEN CASE
            WHEN month_32 = LEAST(month_32, month_33, month_34) THEN 32
            WHEN month_33 = LEAST(month_32, month_33, month_34) THEN 33
            ELSE 34
        END
        WHEN month_33 > 0
        AND month_34 > 0
        AND month_35 > 0 THEN CASE
            WHEN month_33 = LEAST(month_33, month_34, month_35) THEN 33
            WHEN month_34 = LEAST(month_33, month_34, month_35) THEN 34
            ELSE 35
        END
        WHEN month_34 > 0
        AND month_35 > 0
        AND month_36 > 0 THEN CASE
            WHEN month_34 = LEAST(month_34, month_35, month_36) THEN 34
            WHEN month_35 = LEAST(month_34, month_35, month_36) THEN 35
            ELSE 36
        END
        WHEN month_35 > 0
        AND month_36 > 0
        AND month_37 > 0 THEN CASE
            WHEN month_35 = LEAST(month_35, month_36, month_37) THEN 35
            WHEN month_36 = LEAST(month_35, month_36, month_37) THEN 36
            ELSE 37
        END
        WHEN month_36 > 0
        AND month_37 > 0
        AND month_38 > 0 THEN CASE
            WHEN month_36 = LEAST(month_36, month_37, month_38) THEN 36
            WHEN month_37 = LEAST(month_36, month_37, month_38) THEN 37
            ELSE 38
        END
        WHEN month_37 > 0
        AND month_38 > 0
        AND month_39 > 0 THEN CASE
            WHEN month_37 = LEAST(month_37, month_38, month_39) THEN 37
            WHEN month_38 = LEAST(month_37, month_38, month_39) THEN 38
            ELSE 39
        END
        WHEN month_38 > 0
        AND month_39 > 0
        AND month_40 > 0 THEN CASE
            WHEN month_38 = LEAST(month_38, month_39, month_40) THEN 38
            WHEN month_39 = LEAST(month_38, month_39, month_40) THEN 39
            ELSE 40
        END
        WHEN month_39 > 0
        AND month_40 > 0
        AND month_41 > 0 THEN CASE
            WHEN month_39 = LEAST(month_39, month_40, month_41) THEN 39
            WHEN month_40 = LEAST(month_39, month_40, month_41) THEN 40
            ELSE 41
        END
        WHEN month_40 > 0
        AND month_41 > 0
        AND month_42 > 0 THEN CASE
            WHEN month_40 = LEAST(month_40, month_41, month_42) THEN 40
            WHEN month_41 = LEAST(month_40, month_41, month_42) THEN 41
            ELSE 42
        END
        WHEN month_41 > 0
        AND month_42 > 0
        AND month_43 > 0 THEN CASE
            WHEN month_41 = LEAST(month_41, month_42, month_43) THEN 41
            WHEN month_42 = LEAST(month_41, month_42, month_43) THEN 42
            ELSE 43
        END
        WHEN month_42 > 0
        AND month_43 > 0
        AND month_44 > 0 THEN CASE
            WHEN month_42 = LEAST(month_42, month_43, month_44) THEN 42
            WHEN month_43 = LEAST(month_42, month_43, month_44) THEN 43
            ELSE 44
        END
        WHEN month_43 > 0
        AND month_44 > 0
        AND month_45 > 0 THEN CASE
            WHEN month_43 = LEAST(month_43, month_44, month_45) THEN 43
            WHEN month_44 = LEAST(month_43, month_44, month_45) THEN 44
            ELSE 45
        END
        WHEN month_44 > 0
        AND month_45 > 0
        AND month_46 > 0 THEN CASE
            WHEN month_44 = LEAST(month_44, month_45, month_46) THEN 44
            WHEN month_45 = LEAST(month_44, month_45, month_46) THEN 45
            ELSE 46
        END
        WHEN month_45 > 0
        AND month_46 > 0
        AND month_47 > 0 THEN CASE
            WHEN month_45 = LEAST(month_45, month_46, month_47) THEN 45
            WHEN month_46 = LEAST(month_45, month_46, month_47) THEN 46
            ELSE 47
        END
        WHEN month_46 > 0
        AND month_47 > 0
        AND month_48 > 0 THEN CASE
            WHEN month_46 = LEAST(month_46, month_47, month_48) THEN 46
            WHEN month_47 = LEAST(month_46, month_47, month_48) THEN 47
            ELSE 48
        END
        WHEN month_47 > 0
        AND month_48 > 0
        AND month_49 > 0 THEN CASE
            WHEN month_47 = LEAST(month_47, month_48, month_49) THEN 47
            WHEN month_48 = LEAST(month_47, month_48, month_49) THEN 48
            ELSE 49
        END
        WHEN month_48 > 0
        AND month_49 > 0
        AND month_50 > 0 THEN CASE
            WHEN month_48 = LEAST(month_48, month_49, month_50) THEN 48
            WHEN month_49 = LEAST(month_48, month_49, month_50) THEN 49
            ELSE 50
        END
        WHEN month_49 > 0
        AND month_50 > 0
        AND month_51 > 0 THEN CASE
            WHEN month_49 = LEAST(month_49, month_50, month_51) THEN 49
            WHEN month_50 = LEAST(month_49, month_50, month_51) THEN 50
            ELSE 51
        END
        WHEN month_50 > 0
        AND month_51 > 0
        AND month_52 > 0 THEN CASE
            WHEN month_50 = LEAST(month_50, month_51, month_52) THEN 50
            WHEN month_51 = LEAST(month_50, month_51, month_52) THEN 51
            ELSE 52
        END
        WHEN month_51 > 0
        AND month_52 > 0
        AND month_53 > 0 THEN CASE
            WHEN month_51 = LEAST(month_51, month_52, month_53) THEN 51
            WHEN month_52 = LEAST(month_51, month_52, month_53) THEN 52
            ELSE 53
        END
        WHEN month_52 > 0
        AND month_53 > 0
        AND month_54 > 0 THEN CASE
            WHEN month_52 = LEAST(month_52, month_53, month_54) THEN 52
            WHEN month_53 = LEAST(month_52, month_53, month_54) THEN 53
            ELSE 54
        END
        WHEN month_53 > 0
        AND month_54 > 0
        AND month_55 > 0 THEN CASE
            WHEN month_53 = LEAST(month_53, month_54, month_55) THEN 53
            WHEN month_54 = LEAST(month_53, month_54, month_55) THEN 54
            ELSE 55
        END
        WHEN month_54 > 0
        AND month_55 > 0
        AND month_56 > 0 THEN CASE
            WHEN month_54 = LEAST(month_54, month_55, month_56) THEN 54
            WHEN month_55 = LEAST(month_54, month_55, month_56) THEN 55
            ELSE 56
        END
        WHEN month_55 > 0
        AND month_56 > 0
        AND month_57 > 0 THEN CASE
            WHEN month_55 = LEAST(month_55, month_56, month_57) THEN 55
            WHEN month_56 = LEAST(month_55, month_56, month_57) THEN 56
            ELSE 57
        END
        WHEN month_56 > 0
        AND month_57 > 0
        AND month_58 > 0 THEN CASE
            WHEN month_56 = LEAST(month_56, month_57, month_58) THEN 56
            WHEN month_57 = LEAST(month_56, month_57, month_58) THEN 57
            ELSE 58
        END
        WHEN month_57 > 0
        AND month_58 > 0
        AND month_59 > 0 THEN CASE
            WHEN month_57 = LEAST(month_57, month_58, month_59) THEN 57
            WHEN month_58 = LEAST(month_57, month_58, month_59) THEN 58
            ELSE 59
        END
        WHEN month_58 > 0
        AND month_59 > 0
        AND month_60 > 0 THEN CASE
            WHEN month_58 = LEAST(month_58, month_59, month_60) THEN 58
            WHEN month_59 = LEAST(month_58, month_59, month_60) THEN 59
            ELSE 60
        END
        ELSE NULL
    END AS month
FROM
    t_SAL_ever_sol
GROUP BY
    crn;

analyze t_SAL_ever_sol_1;

DROP TABLE IF EXISTS t_imputed_income_1;

CREATE TEMP TABLE t_imputed_income_1 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    *,
    CASE
        WHEN inf_index_value >= 100 THEN (salary * 363)::decimal / inf_index_value
        ELSE NULL
    END AS imputed_income
FROM
    (
        SELECT
            A.*,
            B.inf_index_value
        FROM
            (
                SELECT
                    *,
                    DATEADD(
                        month,
                        -(month - 1),
                        TO_DATE(ADD_MONTHS(v_etl_end_date::DATE, -1), 'YYYY-MM-DD')
                    ) AS salary_month,
                    EXTRACT(
                        YEAR
                        FROM
                            DATEADD(
                                month,
                                -(month - 1),
                                TO_DATE(ADD_MONTHS(v_etl_end_date::DATE, -1), 'YYYY-MM-DD')
                            )
                    ) AS year
                FROM
                    t_SAL_ever_sol_1
                WHERE
                    salary > 18000
            ) AS A
            LEFT JOIN kmbl_ra.bba_ra_papq.risk_inflation_index AS B ON A.year = B.year_val
    ) AS imputed_income_1;

analyze t_imputed_income_1;

DROP TABLE IF EXISTS t_Bureau;

CREATE TEMP TABLE t_Bureau diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    DATE_OPENED,
    Pay_Hist_End_Date,
    tenor,
    Loan_Type_new,
    Ownership_type,
    Loan_Status,
    DATE_CLOSED,
    sector,
    Loan_Type,
    Sanction_Amount,
    Out_standing_Balance,
    EMI,
    High_Credit_Amount
FROM
    kmbl_dex.bl_vw.MISC_EBIX_CIBIL_DATA_TL
WHERE
    report_month = to_char(to_date(v_etl_end_date,'YYYY-MM-DD'),'YYYYMM')::int
AND base in ('RL','Asset');
	
analyze t_Bureau;

DROP TABLE IF EXISTS t_Bureau_HL;

CREATE TEMP TABLE t_Bureau_HL diststyle key distkey(crn) sortkey(crn) AS
SELECT
    *
FROM
    t_Bureau
WHERE
    Loan_Type = 'Home Loan';

analyze t_Bureau_HL;

-- Step 1: Create Bureau_HL_1
DROP TABLE IF EXISTS t_Bureau_HL_1;

-- Using lowercase, unquoted identifiers (recommended for temp tables)
v_sql := 'CREATE TEMP TABLE t_bureau_hl_1 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    a.*,
    b.slc_' || v_slc1 || ' AS slc_' || v_slc1 || ',
    b.slc_' || v_slc2 || ' AS slc_' || v_slc2 || ',
    b.slc_' || v_slc3 || ' AS slc_' || v_slc3 || '
FROM
    t_bureau_hl a
    LEFT JOIN t_slc_last6m b ON a.crn = b.crn';

EXECUTE v_sql;
analyze t_Bureau_HL_1;

DROP TABLE IF EXISTS t_Bureau_HL_2;

CREATE TEMP TABLE t_Bureau_HL_2 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    a.*,
    b.imputed_income
FROM
    t_Bureau_HL_1 a
    LEFT JOIN t_imputed_income_1 b ON a.crn = b.crn;
	
analyze t_Bureau_HL_2;

DROP TABLE IF EXISTS t_Bureau_HL_3;

CREATE TEMP TABLE t_Bureau_HL_3 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    a.*,
    b.LOS_INCOME_AFF
FROM
    t_Bureau_HL_2 a
    LEFT JOIN t_los_income_2 b ON a.crn = b.crn;

analyze t_Bureau_HL_3;

DROP TABLE IF EXISTS t_Bureau_HL_4;

v_sql := 'CREATE TEMP TABLE t_Bureau_HL_4 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    *,
    -- Step 1: Apply threshold logic to SLC values
    CASE
        WHEN SLC_' || v_slc1 || ' < 15000 THEN 0
        ELSE SLC_' || v_slc1 || '
    END AS MM,
    CASE
        WHEN SLC_' || v_slc2 || ' < 15000 THEN 0
        ELSE SLC_' || v_slc2 || '
    END AS NN,
    CASE
        WHEN SLC_' || v_slc3 || ' < 15000 THEN 0
        ELSE SLC_' || v_slc3 || '
    END AS OO,
    -- Step 2: Calculate Min_Salary1
    CASE
        WHEN SLC_' || v_slc1 || ' < 15000 THEN 0
        WHEN SLC_' || v_slc1 || ' >= 15000
         AND SLC_' || v_slc2 || ' >= 15000
         AND SLC_' || v_slc3 || ' >= 15000
            THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc2 || ', SLC_' || v_slc3 || ')
        WHEN SLC_' || v_slc1 || ' >= 15000
         AND SLC_' || v_slc2 || ' >= 15000
            THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc2 || ')
        WHEN SLC_' || v_slc1 || ' >= 15000
         AND SLC_' || v_slc3 || ' >= 15000
            THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc3 || ')
        ELSE 0
    END AS Min_Salary1,
    -- Step 3: Calculate Min_Salary2
    CASE
        WHEN CASE
            WHEN SLC_' || v_slc1 || ' < 15000 THEN 0
            WHEN SLC_' || v_slc1 || ' >= 15000
             AND SLC_' || v_slc2 || ' >= 15000
             AND SLC_' || v_slc3 || ' >= 15000
                THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc2 || ', SLC_' || v_slc3 || ')
            WHEN SLC_' || v_slc1 || ' >= 15000
             AND SLC_' || v_slc2 || ' >= 15000
                THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc2 || ')
            WHEN SLC_' || v_slc1 || ' >= 15000
             AND SLC_' || v_slc3 || ' >= 15000
                THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc3 || ')
            ELSE 0
        END = 0 THEN imputed_income
        ELSE CASE
            WHEN SLC_' || v_slc1 || ' >= 15000
             AND SLC_' || v_slc2 || ' >= 15000
             AND SLC_' || v_slc3 || ' >= 15000
                THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc2 || ', SLC_' || v_slc3 || ')
            WHEN SLC_' || v_slc1 || ' >= 15000
             AND SLC_' || v_slc2 || ' >= 15000
                THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc2 || ')
            WHEN SLC_' || v_slc1 || ' >= 15000
             AND SLC_' || v_slc3 || ' >= 15000
                THEN LEAST(SLC_' || v_slc1 || ', SLC_' || v_slc3 || ')
            ELSE 0
        END
    END AS Min_Salary2,
    -- Step 4: Final Min_Salary
    CASE
        WHEN Min_Salary2 IS NULL OR Min_Salary2 = 0 THEN 0
        ELSE Min_Salary2
    END AS Min_Salary,
    -- Step 5: Source_of_Income flag
    CASE
        WHEN (
            CASE
                WHEN Min_Salary2 IS NULL OR Min_Salary2 = 0 THEN 0
                ELSE Min_Salary2
            END > 0
        )
        OR LOS_INCOME_AFF > 0 THEN 1
        ELSE 0
    END AS Source_of_Income
FROM
    t_Bureau_HL_3';

EXECUTE v_sql;
analyze t_Bureau_HL_4;

DROP TABLE IF EXISTS t_Obli_bureau;

v_sql := 'CREATE TEMP TABLE t_Obli_bureau diststyle key distkey(crn) sortkey(crn) AS
SELECT
    crn,
    date_opened,
    Pay_Hist_End_Date,
    tenor,
    loan_type_new,
    ownership_type,
    loan_status,
    date_closed,
    sector,
    loan_type,
    sanction_amount,
    out_standing_balance,
    emi,
    high_credit_amount,
    SLC_' || v_slc1 || ',
    SLC_' || v_slc2 || ',
    SLC_' || v_slc3 || ',
    imputed_income,
    los_income_aff,
    mm,
    nn,
    oo,
    min_salary1,
    min_salary2,
    min_salary,
    source_of_income
FROM
    t_Bureau_HL_4

UNION ALL

SELECT
    crn,
    date_opened,
    Pay_Hist_End_Date,
    tenor,
    loan_type_new,
    ownership_type,
    loan_status,
    date_closed,
    sector,
    loan_type,
    sanction_amount,
    out_standing_balance,
    emi,
    high_credit_amount,
    NULL AS SLC_' || v_slc1 || ',
    NULL AS SLC_' || v_slc2 || ',
    NULL AS SLC_' || v_slc3 || ',
    NULL AS imputed_income,
    NULL AS los_income_aff,
    NULL AS mm,
    NULL AS nn,
    NULL AS oo,
    NULL AS min_salary1,
    NULL AS min_salary2,
    NULL AS min_salary,
    NULL AS source_of_income
FROM
    t_Bureau
WHERE
    NVL(loan_type, ''x'') <> ''Home Loan''';

EXECUTE v_sql;
analyze t_Obli_bureau;

UPDATE
    t_Obli_bureau
SET
    loan_type = CASE
        WHEN loan_type_new = 'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS' THEN 'Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS'
        WHEN loan_type_new = 'Kisan Credit Card' THEN 'Kisan Credit Card'
        ELSE loan_type
    END;

DROP TABLE IF EXISTS temp_aff_obli_mar25;

CREATE TEMP TABLE temp_aff_obli_mar25 diststyle key distkey(crn) sortkey(crn) AS
SELECT
    *,
    DATEDIFF(month, (case when DATE_OPENED isnull then pay_hist_end_date else DATE_OPENED end), ADD_MONTHS(v_etl_end_date::DATE, -1)) AS mob,
   CASE
    WHEN tenor IS NULL THEN 0
    ELSE tenor - DATEDIFF(month, DATE_OPENED, ADD_MONTHS(v_etl_end_date::DATE, -1))
	END AS remain_tenor,
    CASE
        WHEN UPPER(sector) = 'NOT DISCLOSED' THEN 1
        WHEN UPPER(sector) <> 'NOT DISCLOSED'
        AND (
            COALESCE(tenor, 0) - DATEDIFF(month, DATE_OPENED, ADD_MONTHS(v_etl_end_date::DATE, -1))
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
FROM t_Obli_bureau
WHERE
    nvl(Ownership_type,'x') NOT IN (
        'Authorised User(refers to supplementary card holder)',
        'Guarantor'
    )
    AND NOT (
        Loan_Status = 'Closed'
        AND DATE_CLOSED IS NOT NULL
    );

analyze temp_aff_obli_mar25; 





CALL bba_ra_papq.sp_bureau_obligation_split1(); 





delete from kmbl_ra.bba_ra_papq.BUREAU_OBLIGATION where report_month=to_char(to_date(v_etl_end_date,'YYYY-MM-DD'),'YYYYMM')::int;

INSERT INTO kmbl_ra.bba_ra_papq.BUREAU_OBLIGATION
(
    report_month,
    crn,
    aff_emi,
    emi_unsec,
    aff_emi_topup,
    emi_unsec_topup,
    current_emi,
    etl_inserted_time,
    etl_updated_time
)
SELECT
    to_char(to_date(v_etl_end_date,'YYYY-MM-DD'),'YYYYMM')::int as report_month,
    crn,
    SUM(final_affl_emi_4) AS Aff_EMI,
    SUM(final_affl_emi_4_Unsec) AS EMI_unsec,
    SUM(final_affl_emi_4_topup) AS Aff_EMI_topup,
    SUM(final_affl_emi4_Unsec_topup) AS EMI_unsec_topup,
    SUM(current_emi) AS current_emi,
    CONVERT_TIMEZONE('UTC','Asia/Kolkata',current_timestamp::timestamp) as etl_inserted_time,
    CONVERT_TIMEZONE('UTC','Asia/Kolkata',current_timestamp::timestamp) as etl_updated_time 
FROM
    t_aff_obli_mar25
GROUP BY
    crn;



END;
