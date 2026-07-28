import duckdb
import pandas as pd

bu_input_file = "scrub.csv"
enq_input_file = "enq.csv"
bu_feats_output = "BU_Feats.csv"
bu_tl_output = "BU_TL.csv"

def main():

    # Connect to DuckDB
    con = duckdb.connect("mydb.duckdb")

    PP_HS_BASE_BU_TL_1 = duckdb.sql(f"""SELECT * FROM read_csv_auto('{bu_input_file}') """).df()

    duckdb.sql("""create table PP_HS_BASE_BU_TL_2 as
    select *,(strptime(report_month::VARCHAR || '01', '%Y%m%d')- INTERVAL '1 day')::DATE AS scrub_date,
    case upper(loan_type_new)
                when 'AUTO LOAN (PERSONAL)' then 1
                when 'HOUSING LOAN' then 2
                when 'PROPERTY LOAN' then 3
                when 'LOAN AGAINST SHARES/SECURITIES' then 4
                when 'LOAN AGAINST SHARES / SECURITIES' then 4
                when 'PERSONAL LOAN' then 5
                when 'CONSUMER LOAN' then 6
                when 'GOLD LOAN' then 7
                when 'EDUCATION LOAN' then 8
                when 'LOAN TO PROFESSIONAL' then 9
                when 'CREDIT CARD' then 10
                when 'LEASING' then 11
                when 'OVERDRAFT' then 12
                when 'TWO-WHEELER LOAN' then 13
                when 'NON-FUNDED CREDIT FACILITY' then 14
                when 'LOAN AGAINST BANK DEPOSITS' then 15
                when 'FLEET CARD' then 16
                when 'COMMERCIAL VEHICLE LOAN' then 17
                when 'TELCO - WIRELESS' then 18
                when 'TELCO - BROADBAND' then 19
                when 'TELCO - LANDLINE' then 20
                when 'SELLER FINANCING' then 21
                when 'SELLER FINANCING SOFT (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 22
                when 'GECL LOAN SECURED' then 23
                when 'GECL LOAN UNSECURED' then 24
                when 'SECURED CREDIT CARD' then 31
                when 'USED CAR LOAN' then 32
                when 'CONSTRUCTION EQUIPMENT LOAN' then 33
                when 'TRACTOR LOAN' then 34
                when 'CORPORATE CREDIT CARD' then 35
                when 'KISAN CREDIT CARD' then 36
                when 'LOAN ON CREDIT CARD' then 37
                when 'PRIME MINISTER JAAN DHAN YOJANA - OVERDRAFT' then 38
                when 'MUDRA LOANS - SHISHU / KISHOR / TARUN' then 39
                when 'MICROFINANCE - BUSINESS LOAN' then 40
                when 'MICROFINANCE - PERSONAL LOAN' then 41
                when 'MICROFINANCE - HOUSING LOAN' then 42
                when 'MICROFINANCE - OTHER' then 43
                when 'MICROFINANCE - OTHERS' then 43
                when 'PRADHAN MANTRI AWAS YOJANA - CREDIT LINK SUBSIDY SCHEME MAY CLSS' then 44
                when 'P2P PERSONAL LOAN' then 45
                when 'P2P AUTO LOAN' then 46
                when 'P2P EDUCATION LOAN' then 47
                when 'BUSINESS LOAN - SECURED' then 50
                when 'BUSINESS LOAN - GENERAL' then 51
                when 'BUSINESS LOAN - PRIORITY SECTOR - SMALL BUSINESS' then 52
                when 'BUSINESS LOAN - PRIORITY SECTOR - AGRICULTURE' then 53
                when 'BUSINESS LOAN - PRIORITY SECTOR - OTHERS' then 54
                when 'BUSINESS NON-FUNDED CREDIT FACILITY - GENERAL' then 55
                when 'BUSINESS NON-FUNDED CREDIT FACILITY - PRIORITY SECTOR - SMALL BUSINESS' then 56
                when 'BUSINESS NON-FUNDED CREDIT FACILITY-PRIORITY SECTOR- SMALL BUSINESS' then 56
                when 'BUSINESS NON-FUNDED CREDIT FACILITY - PRIORITY SECTOR - AGRICULTURE' then 57
                when 'BUSINESS NON-FUNDED CREDIT FACILITY-PRIORITY SECTOR-AGRICULTURE' then 57
                when 'BUSINESS NON-FUNDED CREDIT FACILITY - PRIORITY SECTOR-OTHERS' then 58
                when 'BUSINESS NON-FUNDED CREDIT FACILITY-PRIORITY SECTOR-OTHERS' then 58
                when 'BUSINESS LOAN AGAINST BANK DEPOSITS' then 59
                when 'BUSINESS LOAN - UNSECURED' then 61
                when 'SHORT TERM PERSONAL LOAN' then 69
                when 'PRIORITY SECTOR - GOLD LOAN' then 70
                when 'TEMPORARY OVERDRAFT' then 71
                when 'MICROFINANCE DETAILED REPORT (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 80
                when 'SUMMARY REPORT (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 81
                when 'LOCATE PLUS FOR INSURANCE (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 88
                when 'ACCOUNT REVIEW (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 90
                when 'RETRO ENQUIRY (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 91
                when 'LOCATE PLUS (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 92
                when 'ADVISER LIABILITY (APPLICABLE TO ENQUIRY PURPOSE ONLY)' then 97
                when 'SECURED (ACCOUNT GROUP FOR PORTFOLIO REVIEW RESPONSE)' then 98
                when 'UNSECURED (ACCOUNT GROUP FOR PORTFOLIO REVIEW RESPONSE)' then 99
                when 'OTHER' then 0
                when 'NONE'  then 0
                else 0
            end::int as account_type_cd,
    
    (scrub_date - INTERVAL '3 MONTH')::DATE as datebck3,
    (scrub_date - INTERVAL '6 MONTH')::date  as datebck6,
    (scrub_date - INTERVAL '9 MONTH')::date  as datebck9,
    (scrub_date - INTERVAL '12 MONTH')::date  as datebck12,
    (scrub_date - INTERVAL '18 MONTH')::date  as datebck18,
    (scrub_date - INTERVAL '24 MONTH')::date  as datebck24,
    (scrub_date - INTERVAL '36 MONTH')::date  as datebck36,
    
    greatest(out_standing_balance, 0) as out_standing_balance_clean,
    greatest(over_due_amount, 0)      as over_due_amount_clean,
    case 
                when upper(loan_type_new) in (
                    'CREDIT CARD','SECURED CREDIT CARD','CORPORATE CREDIT CARD',
                    'KISAN CREDIT CARD','FLEET CARD'
                ) then
                    case 
                        when creditlimit > 0 then creditlimit
                        when (creditlimit <= 0 or creditlimit is null)
                             and sanction_amount is null
                             and out_standing_balance_clean is not null
                        then out_standing_balance_clean
                        else sanction_amount
                    end
                else sanction_amount
            end::numeric(18,2) as sanction_amount_adj,
    
    case when sanction_amount_adj <=  10000 then 1 else 0 end::int as is_sanc_amt_bel10k,
    case when sanction_amount_adj <=  20000 then 1 else 0 end::int as is_sanc_amt_bel20k,
    case when sanction_amount_adj <= 100000 then 1 else 0 end::int as is_sanc_amt_bel1l,
    case when sanction_amount_adj <= 300000 then 1 else 0 end::int as is_sanc_amt_bel3l,
    
    date_trunc('month',
            case
                when 
                 pay_hist_start_date > scrub_date
                then scrub_date
                else pay_hist_start_date
            end
        )::date as pay_hist_end_month,
     
        date_trunc('month',
            case
                when 
                 pay_hist_start_date > scrub_date
                then scrub_date
                else pay_hist_start_date
            end
        )::date as rec_end_date,
     
        
    (
        date_trunc(
            'month',
            case
                when pay_hist_start_date > scrub_date
                then scrub_date
                else pay_hist_start_date
            end
        )
        - (((char_length(coalesce(dpd_string, '')) / 3) - 1) * INTERVAL '1 MONTH')
    )::DATE AS rec_start_date,
    
        case 
                when date_opened is null
                     and char_length(coalesce(dpd_string,'')) < 108
                     and rec_start_date is not null
                then rec_start_date
                else date_opened
            end as date_opened_filled,
    
        case 
                when 
                    (date_opened_filled is not null or datereported_trades is not null)
                    and upper(loan_type_new) not in (
                        'CREDIT CARD','SECURED CREDIT CARD','CORPORATE CREDIT CARD',
                        'KISAN CREDIT CARD','FLEET CARD'
                    )
                    and out_standing_balance_clean <= 0
                then 1
                when 
                    (date_opened_filled is not null or datereported_trades is not null)
                    and date_closed IS NOT NULL
                    THEN 1
                WHEN  (date_opened_filled is not null or datereported_trades is not null)
                    AND date_closed IS NULL
          THEN 0
          ELSE NULL 
        END::int AS close_flag,
    
        coalesce(
                date_closed,
                case 
                    when close_flag = 1 
                         and date_closed is null 
                         and last_payment_date is not null
                    then last_payment_date
                    else null
                end,
                case 
                    when close_flag = 1
                         and date_closed is null
                         and last_payment_date is null
                         and datereported_trades is not null
                    then datereported_trades
                    else null
                end
            ) as date_closed_filled,
    
        CASE
                WHEN close_flag IS NULL THEN NULL
                ELSE 1 - close_flag
                END::int AS open_flag,
        case 
                when date_opened_filled is not null and scrub_date is not null
                then round( (datediff('day', date_opened_filled, scrub_date)::numeric / 30.5), 2)
                else null
            end as time_since_tr_open,
            case 
                when date_closed_filled is not null and scrub_date is not null
                then round( (datediff('day', date_closed_filled, scrub_date)::numeric / 30.5), 2)
                else null
            end as time_since_tr_close
     from PP_HS_BASE_BU_TL_1
    where
     date_opened <= scrub_date;
    
    
    create table PP_HS_BASE_BU_TL_3 as
    with nums as (
        select 1 as idx union all select 2  union all select 3  union all select 4  union all select 5 union all
        select 6 union all select 7  union all select 8  union all select 9  union all select 10 union all
        select 11 union all select 12 union all select 13 union all select 14 union all select 15 union all
        select 16 union all select 17 union all select 18 union all select 19 union all select 20 union all
        select 21 union all select 22 union all select 23 union all select 24 union all select 25 union all
        select 26 union all select 27 union all select 28 union all select 29 union all select 30 union all
        select 31 union all select 32 union all select 33 union all select 34 union all select 35 union all
        select 36 union all select 37 union all select 38 union all select 39 union all select 40
    ),
    
    op13 as (
        -- compute dpd_processed in one grouped step (no correlated subquery)
        select
            o.crn,
            o.reference_date,
            o.report_month,
            o.CV_RN,
            o.creditlimit,
            o.date_closed_filled         as date_closed,
            o.date_opened_filled         as date_opened,
            o.datereported_trades,
            o.dpd_string,
            -- EXACT same logic as your working one_row snippet, but per row
            string_agg(
                CASE
                WHEN UPPER(TRIM(substring(o.dpd_string FROM (n.idx - 1) * 3 + 1 FOR 3))) = 'STD' THEN
                    CASE
                    WHEN n.idx = 1 THEN
                        CASE
                        WHEN COALESCE(o.emi, 0) > 0 AND COALESCE(o.over_due_amount_clean, 0) >= 500 THEN
                            -- Padded 3-char day count
                            LPAD(
                            CAST(
                                CASE
                                WHEN CEIL(COALESCE(o.over_due_amount_clean, 0)::numeric / NULLIF(COALESCE(o.emi, 0)::numeric, 0)) * 30 > 900 THEN 900
                                WHEN CEIL(COALESCE(o.over_due_amount_clean, 0)::numeric / NULLIF(COALESCE(o.emi, 0)::numeric, 0)) * 30 = 0 THEN 30
                                ELSE CEIL(COALESCE(o.over_due_amount_clean, 0)::numeric / NULLIF(COALESCE(o.emi, 0)::numeric, 0)) * 30
                                END AS INT
                            )::varchar,
                            3, '0'
                            )
    
                        WHEN COALESCE(o.emi, 0) <= 0 AND COALESCE(o.over_due_amount_clean, 0) >= 500 THEN '030'
                        WHEN COALESCE(o.over_due_amount_clean, 0) < 500 THEN '000'
                        ELSE '000'
                        END
                    ELSE '000'
                    END
    
    
                    when substring(o.dpd_string from (n.idx - 1)*3 + 1 for 3) = 'SUB' then '091'
                    when substring(o.dpd_string from (n.idx - 1)*3 + 1 for 3) = 'DBT' then '181'
                    when substring(o.dpd_string from (n.idx - 1)*3 + 1 for 3) = 'LSS' then '361'
                    when substring(o.dpd_string from (n.idx - 1)*3 + 1 for 3) = 'SMA' then '061'
                    when substring(o.dpd_string from (n.idx - 1)*3 + 1 for 3) in ('X','XX','XXX') then '   '
    
                    else substring(o.dpd_string from (n.idx - 1)*3 + 1 for 3)
                end,
                '' order by n.idx
            )  as dpd_processed,
            o.pay_hist_end_date,
            o.pay_hist_start_date,
            o.rec_start_date,
            o.rec_end_date,
            o.sanction_amount_adj        as sanction_amount,
            o.out_standing_balance_clean as out_standing_balance,
            o.over_due_amount_clean      as over_due_amount,
            o.emi,
            o.high_credit_amount,
            o.tu_score,
            o.last_payment_date,
            o.loan_type_new,
            o.loan_status,
            o.loan_classification,
            o.ownership_type,
            o.sector,
            o.base,
            o.account_type_cd,
            o.is_sanc_amt_bel10k,
            o.is_sanc_amt_bel20k,
            o.is_sanc_amt_bel1l,
            o.is_sanc_amt_bel3l,
            o.open_flag,
            o.close_flag,
            o.scrub_date,
            o.datebck3,
            o.datebck6,
            o.datebck9,
            o.datebck12,
            o.datebck18,
            o.datebck24,
            o.datebck36,
            o.time_since_tr_open,
            o.time_since_tr_close
        from PP_HS_BASE_BU_TL_2 o
        left join nums n
          on n.idx <= ceil(char_length(coalesce(o.dpd_string,''))::numeric / 3)
        group by
            o.crn,
            o.reference_date,
            o.report_month,
            o.CV_RN,
            o.creditlimit,
            o.date_closed_filled,
            o.date_opened_filled,
            o.datereported_trades,
            o.dpd_string,
            o.pay_hist_end_date,
            o.pay_hist_start_date,
            o.rec_start_date,
            o.rec_end_date,
            o.sanction_amount_adj,
            o.out_standing_balance_clean,
            o.over_due_amount_clean,
            o.emi,
            o.high_credit_amount,
            o.tu_score,
            o.last_payment_date,
            o.loan_type_new,
            o.loan_status,
            o.loan_classification,
            o.ownership_type,
            o.sector,
            o.base,
            o.account_type_cd,
            o.is_sanc_amt_bel10k,
            o.is_sanc_amt_bel20k,
            o.is_sanc_amt_bel1l,
            o.is_sanc_amt_bel3l,
            o.open_flag,
            o.close_flag,
            o.scrub_date,
            o.datebck3,
            o.datebck6,
            o.datebck9,
            o.datebck12,
            o.datebck18,
            o.datebck24,
            o.datebck36,
            o.time_since_tr_open,
            o.time_since_tr_close
    )
    select * from op13;

    create table PP_HS_BASE_BU_TL_4 as
        select *,
        date_trunc('month', o.rec_end_date)::date   as rec_end_month,
                date_trunc('month', o.scrub_date)::date     as scrub_month,
                (char_length(coalesce(o.dpd_processed, '')) / 3)::int as hist_months 
        from PP_HS_BASE_BU_TL_3 o;
        """)

    duckdb.sql("""create table PP_HS_BASE_BU_TL_5 as
        select *,
        case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '35 MONTH',  -- T-36
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '35 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_36,
        
            -- T-35 (t_35)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '34 MONTH',  -- T-35
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '34 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_35,
        
            -- T-34 (t_34)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '33 MONTH',  -- T-34
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '33 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_34,
        
            -- T-33 (t_33)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '32 MONTH',  -- T-33
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '32 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_33,
        
            -- T-32 (t_32)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '31 MONTH',  -- T-32
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '31 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_32,
        
            -- T-31 (t_31)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '30 MONTH',  -- T-31
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '30 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_31,
        
            -- T-30 (t_30)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '29 MONTH',  -- T-30
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '29 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_30,
        
            -- T-29 (t_29)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '28 MONTH',  -- T-29
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '28 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_29,
        
            -- T-28 (t_28)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '27 MONTH',  -- T-28
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '27 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_28,
        
            -- T-27 (t_27)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '26 MONTH',  -- T-27
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '26 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_27,
        
            -- T-26 (t_26)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '25 MONTH',  -- T-26
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '25 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_26,
        
            -- T-25 (t_25)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '24 MONTH',  -- T-25
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '24 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_25,
        
            -- T-24 (t_24)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '23 MONTH',  -- T-24
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '23 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_24,
        
            -- T-23 (t_23)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '22 MONTH',  -- T-23
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '22 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_23,
        
            -- T-22 (t_22)
            case
                when hist_months is null or hist_months <= 0
                    or rec_end_month is null
                    or scrub_month   is null
                then null::int
                when datediff(
                        'month',
                        scrub_month - INTERVAL '21 MONTH',  -- T-22
                        rec_end_month
                    ) not between 0 and hist_months - 1
                then null::int
                else cast(
                    nullif(
                        trim(
                            substring(
                                dpd_processed,
                                (
                                    datediff(
                                        'month',
                                        scrub_month - INTERVAL '21 MONTH',
                                        rec_end_month
                                    ) * 3 + 1
                                )::int,
                                3
                            )
                        ),
                        ''
                    ) as int
                )
            end as t_22,

-- T-21 (t_21)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '20 MONTH',  -- T-21
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '20 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_21,
    
        -- T-20 (t_20)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '19 MONTH',  -- T-20
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '19 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_20,
    
        -- T-19 (t_19)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '18 MONTH',  -- T-19
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '18 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_19,
    
        -- T-18 (t_18)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '17 MONTH',  -- T-18
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '17 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_18,
    
        -- T-17 (t_17)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '16 MONTH',  -- T-17
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '16 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_17,
    
        -- T-16 (t_16)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '15 MONTH',  -- T-16
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '15 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_16,
    
        -- T-15 (t_15)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '14 MONTH',  -- T-15
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '14 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_15,
    
        -- T-14 (t_14)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '13 MONTH',  -- T-14
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '13 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_14,
    
        -- T-13 (t_13)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '12 MONTH',  -- T-13
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '12 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_13,
    
        -- T-12 (t_12)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '11 MONTH',  -- T-12
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '11 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_12,
    
        -- T-11 (t_11)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '10 MONTH',  -- T-11
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '10 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_11,
    
        -- T-10 (t_10)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '9 MONTH',  -- T-10
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '9 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_10,
    
        -- T-9 (t_9)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '8 MONTH',  -- T-9
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '8 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_9,
    
        -- T-8 (t_8)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '7 MONTH',  -- T-8
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '7 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_8,
    
        -- T-7 (t_7)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '6 MONTH',  -- T-7
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '6 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_7,
    
        -- T-6 (t_6)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '5 MONTH',  -- T-6
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '5 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_6,
    
        -- T-5 (t_5)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '4 MONTH',  -- T-5
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '4 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_5,
    
        -- T-4 (t_4)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '3 MONTH',  -- T-4
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '3 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_4,
    
        -- T-3 (t_3)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '2 MONTH',  -- T-3
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '2 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_3,
    
        -- T-2 (t_2)
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
                     scrub_month - INTERVAL '1 MONTH',  -- T-2
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
                                    scrub_month - INTERVAL '1 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_2,
    
        -- T-1 (t_1) = SCRUB month
        case
            when hist_months is null or hist_months <= 0
                 or rec_end_month is null
                 or scrub_month   is null
            then null::int
            when datediff(
                     'month',
    scrub_month - INTERVAL '0 MONTH',   -- T-1
                     rec_end_month
                 ) not between 0 and hist_months - 1
            then null::int
            else cast(
                nullif(
                    trim(
                        substring(
                            dpd_processed,
                            (
                                datediff(
                                    'month',
    scrub_month - INTERVAL '0 MONTH',
                                    rec_end_month
                                ) * 3 + 1
                            )::int,
                            3
                        )
                    ),
                    ''
                ) as int
            )
        end as t_1
     from PP_HS_BASE_BU_TL_4;""")

    duckdb.sql("""create table PP_HS_BASE_BU_TL_6 as 
    select *,
    (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_3 IS NOT NULL THEN 1
                            WHEN t.t_2 IS NOT NULL THEN 2
                            WHEN t.t_1 IS NOT NULL THEN 3
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_3, 0)
                          + COALESCE(t.t_2, 0)
                          + COALESCE(t.t_1, 0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 3
                                    WHEN t.t_2 IS NOT NULL THEN 2
                                    WHEN t.t_3 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_3 IS NOT NULL THEN 1
                                    WHEN t.t_2 IS NOT NULL THEN 2
                                    WHEN t.t_1 IS NOT NULL THEN 3
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l3m,
    
            /* ====================== last 6 months ====================== */
            (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_6 IS NOT NULL THEN 1
                            WHEN t.t_5 IS NOT NULL THEN 2
                            WHEN t.t_4 IS NOT NULL THEN 3
                            WHEN t.t_3 IS NOT NULL THEN 4
                            WHEN t.t_2 IS NOT NULL THEN 5
                            WHEN t.t_1 IS NOT NULL THEN 6
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_6, 0)
                          + COALESCE(t.t_5, 0)
                          + COALESCE(t.t_4, 0)
                          + COALESCE(t.t_3, 0)
                          + COALESCE(t.t_2, 0)
                          + COALESCE(t.t_1, 0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 6
                                    WHEN t.t_2 IS NOT NULL THEN 5
                                    WHEN t.t_3 IS NOT NULL THEN 4
                                    WHEN t.t_4 IS NOT NULL THEN 3
                                    WHEN t.t_5 IS NOT NULL THEN 2
                                    WHEN t.t_6 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_6 IS NOT NULL THEN 1
                                    WHEN t.t_5 IS NOT NULL THEN 2
                                    WHEN t.t_4 IS NOT NULL THEN 3
                                    WHEN t.t_3 IS NOT NULL THEN 4
                                    WHEN t.t_2 IS NOT NULL THEN 5
                                    WHEN t.t_1 IS NOT NULL THEN 6
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l6m,
    
            /* ====================== last 9 months ====================== */
            (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_9 IS NOT NULL THEN 1
                            WHEN t.t_8 IS NOT NULL THEN 2
                            WHEN t.t_7 IS NOT NULL THEN 3
                            WHEN t.t_6 IS NOT NULL THEN 4
                            WHEN t.t_5 IS NOT NULL THEN 5
                            WHEN t.t_4 IS NOT NULL THEN 6
                            WHEN t.t_3 IS NOT NULL THEN 7
                            WHEN t.t_2 IS NOT NULL THEN 8
                            WHEN t.t_1 IS NOT NULL THEN 9
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_9, 0)
                          + COALESCE(t.t_8, 0)
                          + COALESCE(t.t_7, 0)
                          + COALESCE(t.t_6, 0)
                          + COALESCE(t.t_5, 0)
                          + COALESCE(t.t_4, 0)
                          + COALESCE(t.t_3, 0)
                          + COALESCE(t.t_2, 0)
                          + COALESCE(t.t_1, 0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 9
                                    WHEN t.t_2 IS NOT NULL THEN 8
                                    WHEN t.t_3 IS NOT NULL THEN 7
                                    WHEN t.t_4 IS NOT NULL THEN 6
                                    WHEN t.t_5 IS NOT NULL THEN 5
                                    WHEN t.t_6 IS NOT NULL THEN 4
                                    WHEN t.t_7 IS NOT NULL THEN 3
                                    WHEN t.t_8 IS NOT NULL THEN 2
                                    WHEN t.t_9 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_9 IS NOT NULL THEN 1
                                    WHEN t.t_8 IS NOT NULL THEN 2
                                    WHEN t.t_7 IS NOT NULL THEN 3
                                    WHEN t.t_6 IS NOT NULL THEN 4
                                    WHEN t.t_5 IS NOT NULL THEN 5
                                    WHEN t.t_4 IS NOT NULL THEN 6
                                    WHEN t.t_3 IS NOT NULL THEN 7
                                    WHEN t.t_2 IS NOT NULL THEN 8
                                    WHEN t.t_1 IS NOT NULL THEN 9
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l9m,
    
            /* ====================== last 12 months ====================== */
            (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_12 IS NOT NULL THEN 1
                            WHEN t.t_11 IS NOT NULL THEN 2
                            WHEN t.t_10 IS NOT NULL THEN 3
                            WHEN t.t_9 IS NOT NULL THEN 4
                            WHEN t.t_8 IS NOT NULL THEN 5
                            WHEN t.t_7 IS NOT NULL THEN 6
                            WHEN t.t_6 IS NOT NULL THEN 7
                            WHEN t.t_5 IS NOT NULL THEN 8
                            WHEN t.t_4 IS NOT NULL THEN 9
                            WHEN t.t_3 IS NOT NULL THEN 10
                            WHEN t.t_2 IS NOT NULL THEN 11
                            WHEN t.t_1 IS NOT NULL THEN 12
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_12, 0) + COALESCE(t.t_11, 0)
                          + COALESCE(t.t_10, 0) + COALESCE(t.t_9, 0)
                          + COALESCE(t.t_8, 0)  + COALESCE(t.t_7, 0)
                          + COALESCE(t.t_6, 0)  + COALESCE(t.t_5, 0)
                          + COALESCE(t.t_4, 0)  + COALESCE(t.t_3, 0)
                          + COALESCE(t.t_2, 0)  + COALESCE(t.t_1, 0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 12
                                    WHEN t.t_2 IS NOT NULL THEN 11
                                    WHEN t.t_3 IS NOT NULL THEN 10
                                    WHEN t.t_4 IS NOT NULL THEN 9
                                    WHEN t.t_5 IS NOT NULL THEN 8
                                    WHEN t.t_6 IS NOT NULL THEN 7
                                    WHEN t.t_7 IS NOT NULL THEN 6
                                    WHEN t.t_8 IS NOT NULL THEN 5
                                    WHEN t.t_9 IS NOT NULL THEN 4
                                    WHEN t.t_10 IS NOT NULL THEN 3
                                    WHEN t.t_11 IS NOT NULL THEN 2
                                    WHEN t.t_12 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_12 IS NOT NULL THEN 1
                                    WHEN t.t_11 IS NOT NULL THEN 2
                                    WHEN t.t_10 IS NOT NULL THEN 3
                                    WHEN t.t_9 IS NOT NULL THEN 4
                                    WHEN t.t_8 IS NOT NULL THEN 5
                                    WHEN t.t_7 IS NOT NULL THEN 6
                                    WHEN t.t_6 IS NOT NULL THEN 7
                                    WHEN t.t_5 IS NOT NULL THEN 8
                                    WHEN t.t_4 IS NOT NULL THEN 9
                                    WHEN t.t_3 IS NOT NULL THEN 10
                                    WHEN t.t_2 IS NOT NULL THEN 11
                                    WHEN t.t_1 IS NOT NULL THEN 12
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l12m,
    
            /* ====================== last 18 months ====================== */
            (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_18 IS NOT NULL THEN 1
                            WHEN t.t_17 IS NOT NULL THEN 2
                            WHEN t.t_16 IS NOT NULL THEN 3
                            WHEN t.t_15 IS NOT NULL THEN 4
                            WHEN t.t_14 IS NOT NULL THEN 5
                            WHEN t.t_13 IS NOT NULL THEN 6
                            WHEN t.t_12 IS NOT NULL THEN 7
                            WHEN t.t_11 IS NOT NULL THEN 8
                            WHEN t.t_10 IS NOT NULL THEN 9
                            WHEN t.t_9 IS NOT NULL THEN 10
                            WHEN t.t_8 IS NOT NULL THEN 11
                            WHEN t.t_7 IS NOT NULL THEN 12
                            WHEN t.t_6 IS NOT NULL THEN 13
                            WHEN t.t_5 IS NOT NULL THEN 14
                            WHEN t.t_4 IS NOT NULL THEN 15
                            WHEN t.t_3 IS NOT NULL THEN 16
                            WHEN t.t_2 IS NOT NULL THEN 17
                            WHEN t.t_1 IS NOT NULL THEN 18
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_18,0) + COALESCE(t.t_17,0)
                          + COALESCE(t.t_16,0) + COALESCE(t.t_15,0)
                          + COALESCE(t.t_14,0) + COALESCE(t.t_13,0)
                          + COALESCE(t.t_12,0) + COALESCE(t.t_11,0)
                          + COALESCE(t.t_10,0) + COALESCE(t.t_9,0)
                          + COALESCE(t.t_8,0)  + COALESCE(t.t_7,0)
                          + COALESCE(t.t_6,0)  + COALESCE(t.t_5,0)
                          + COALESCE(t.t_4,0)  + COALESCE(t.t_3,0)
                          + COALESCE(t.t_2,0)  + COALESCE(t.t_1,0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 18
                                    WHEN t.t_2 IS NOT NULL THEN 17
                                    WHEN t.t_3 IS NOT NULL THEN 16
                                    WHEN t.t_4 IS NOT NULL THEN 15
                                    WHEN t.t_5 IS NOT NULL THEN 14
                                    WHEN t.t_6 IS NOT NULL THEN 13
                                    WHEN t.t_7 IS NOT NULL THEN 12
                                    WHEN t.t_8 IS NOT NULL THEN 11
                                    WHEN t.t_9 IS NOT NULL THEN 10
                                    WHEN t.t_10 IS NOT NULL THEN 9
                                    WHEN t.t_11 IS NOT NULL THEN 8
                                    WHEN t.t_12 IS NOT NULL THEN 7
                                    WHEN t.t_13 IS NOT NULL THEN 6
                                    WHEN t.t_14 IS NOT NULL THEN 5
                                    WHEN t.t_15 IS NOT NULL THEN 4
                                    WHEN t.t_16 IS NOT NULL THEN 3
                                    WHEN t.t_17 IS NOT NULL THEN 2
                                    WHEN t.t_18 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_18 IS NOT NULL THEN 1
                                    WHEN t.t_17 IS NOT NULL THEN 2
                                    WHEN t.t_16 IS NOT NULL THEN 3
                                    WHEN t.t_15 IS NOT NULL THEN 4
                                    WHEN t.t_14 IS NOT NULL THEN 5
                                    WHEN t.t_13 IS NOT NULL THEN 6
                                    WHEN t.t_12 IS NOT NULL THEN 7
                                    WHEN t.t_11 IS NOT NULL THEN 8
                                    WHEN t.t_10 IS NOT NULL THEN 9
                                    WHEN t.t_9 IS NOT NULL THEN 10
                                    WHEN t.t_8 IS NOT NULL THEN 11
                                    WHEN t.t_7 IS NOT NULL THEN 12
                                    WHEN t.t_6 IS NOT NULL THEN 13
                                    WHEN t.t_5 IS NOT NULL THEN 14
                                    WHEN t.t_4 IS NOT NULL THEN 15
                                    WHEN t.t_3 IS NOT NULL THEN 16
                                    WHEN t.t_2 IS NOT NULL THEN 17
                                    WHEN t.t_1 IS NOT NULL THEN 18
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l18m,
    
            /* ====================== last 24 months ====================== */
            (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_24 IS NOT NULL THEN 1
                            WHEN t.t_23 IS NOT NULL THEN 2
                            WHEN t.t_22 IS NOT NULL THEN 3
                            WHEN t.t_21 IS NOT NULL THEN 4
                            WHEN t.t_20 IS NOT NULL THEN 5
                            WHEN t.t_19 IS NOT NULL THEN 6
                            WHEN t.t_18 IS NOT NULL THEN 7
                            WHEN t.t_17 IS NOT NULL THEN 8
                            WHEN t.t_16 IS NOT NULL THEN 9
                            WHEN t.t_15 IS NOT NULL THEN 10
                            WHEN t.t_14 IS NOT NULL THEN 11
                            WHEN t.t_13 IS NOT NULL THEN 12
                            WHEN t.t_12 IS NOT NULL THEN 13
                            WHEN t.t_11 IS NOT NULL THEN 14
                            WHEN t.t_10 IS NOT NULL THEN 15
                            WHEN t.t_9 IS NOT NULL THEN 16
                            WHEN t.t_8 IS NOT NULL THEN 17
                            WHEN t.t_7 IS NOT NULL THEN 18
                            WHEN t.t_6 IS NOT NULL THEN 19
                            WHEN t.t_5 IS NOT NULL THEN 20
                            WHEN t.t_4 IS NOT NULL THEN 21
                            WHEN t.t_3 IS NOT NULL THEN 22
                            WHEN t.t_2 IS NOT NULL THEN 23
                            WHEN t.t_1 IS NOT NULL THEN 24
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_24,0) + COALESCE(t.t_23,0) + COALESCE(t.t_22,0) + COALESCE(t.t_21,0)
                          + COALESCE(t.t_20,0) + COALESCE(t.t_19,0) + COALESCE(t.t_18,0) + COALESCE(t.t_17,0)
                          + COALESCE(t.t_16,0) + COALESCE(t.t_15,0) + COALESCE(t.t_14,0) + COALESCE(t.t_13,0)
                          + COALESCE(t.t_12,0) + COALESCE(t.t_11,0) + COALESCE(t.t_10,0) + COALESCE(t.t_9,0)
                          + COALESCE(t.t_8,0)  + COALESCE(t.t_7,0)  + COALESCE(t.t_6,0)  + COALESCE(t.t_5,0)
                          + COALESCE(t.t_4,0)  + COALESCE(t.t_3,0)  + COALESCE(t.t_2,0)  + COALESCE(t.t_1,0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 24
                                    WHEN t.t_2 IS NOT NULL THEN 23
                                    WHEN t.t_3 IS NOT NULL THEN 22
                                    WHEN t.t_4 IS NOT NULL THEN 21
                                    WHEN t.t_5 IS NOT NULL THEN 20
                                    WHEN t.t_6 IS NOT NULL THEN 19
                                    WHEN t.t_7 IS NOT NULL THEN 18
                                    WHEN t.t_8 IS NOT NULL THEN 17
                                    WHEN t.t_9 IS NOT NULL THEN 16
                                    WHEN t.t_10 IS NOT NULL THEN 15
                                    WHEN t.t_11 IS NOT NULL THEN 14
                                    WHEN t.t_12 IS NOT NULL THEN 13
                                    WHEN t.t_13 IS NOT NULL THEN 12
                                    WHEN t.t_14 IS NOT NULL THEN 11
                                    WHEN t.t_15 IS NOT NULL THEN 10
                                    WHEN t.t_16 IS NOT NULL THEN 9
                                    WHEN t.t_17 IS NOT NULL THEN 8
                                    WHEN t.t_18 IS NOT NULL THEN 7
                                    WHEN t.t_19 IS NOT NULL THEN 6
                                    WHEN t.t_20 IS NOT NULL THEN 5
                                    WHEN t.t_21 IS NOT NULL THEN 4
                                    WHEN t.t_22 IS NOT NULL THEN 3
                                    WHEN t.t_23 IS NOT NULL THEN 2
                                    WHEN t.t_24 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_24 IS NOT NULL THEN 1
                                    WHEN t.t_23 IS NOT NULL THEN 2
                                    WHEN t.t_22 IS NOT NULL THEN 3
                                    WHEN t.t_21 IS NOT NULL THEN 4
                                    WHEN t.t_20 IS NOT NULL THEN 5
                                    WHEN t.t_19 IS NOT NULL THEN 6
                                    WHEN t.t_18 IS NOT NULL THEN 7
                                    WHEN t.t_17 IS NOT NULL THEN 8
                                    WHEN t.t_16 IS NOT NULL THEN 9
                                    WHEN t.t_15 IS NOT NULL THEN 10
                                    WHEN t.t_14 IS NOT NULL THEN 11
                                    WHEN t.t_13 IS NOT NULL THEN 12
                                    WHEN t.t_12 IS NOT NULL THEN 13
                                    WHEN t.t_11 IS NOT NULL THEN 14
                                    WHEN t.t_10 IS NOT NULL THEN 15
                                    WHEN t.t_9 IS NOT NULL THEN 16
                                    WHEN t.t_8 IS NOT NULL THEN 17
                                    WHEN t.t_7 IS NOT NULL THEN 18
                                    WHEN t.t_6 IS NOT NULL THEN 19
                                    WHEN t.t_5 IS NOT NULL THEN 20
                                    WHEN t.t_4 IS NOT NULL THEN 21
                                    WHEN t.t_3 IS NOT NULL THEN 22
                                    WHEN t.t_2 IS NOT NULL THEN 23
                                    WHEN t.t_1 IS NOT NULL THEN 24
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l24m,
    
            /* ====================== last 36 months ====================== */
            (
                CASE
                    WHEN (
                        CASE
                            WHEN t.t_36 IS NOT NULL THEN 1
                            WHEN t.t_35 IS NOT NULL THEN 2
                            WHEN t.t_34 IS NOT NULL THEN 3
                            WHEN t.t_33 IS NOT NULL THEN 4
                            WHEN t.t_32 IS NOT NULL THEN 5
                            WHEN t.t_31 IS NOT NULL THEN 6
                            WHEN t.t_30 IS NOT NULL THEN 7
                            WHEN t.t_29 IS NOT NULL THEN 8
                            WHEN t.t_28 IS NOT NULL THEN 9
                            WHEN t.t_27 IS NOT NULL THEN 10
                            WHEN t.t_26 IS NOT NULL THEN 11
                            WHEN t.t_25 IS NOT NULL THEN 12
                            WHEN t.t_24 IS NOT NULL THEN 13
                            WHEN t.t_23 IS NOT NULL THEN 14
                            WHEN t.t_22 IS NOT NULL THEN 15
                            WHEN t.t_21 IS NOT NULL THEN 16
                            WHEN t.t_20 IS NOT NULL THEN 17
                            WHEN t.t_19 IS NOT NULL THEN 18
                            WHEN t.t_18 IS NOT NULL THEN 19
                            WHEN t.t_17 IS NOT NULL THEN 20
                            WHEN t.t_16 IS NOT NULL THEN 21
                            WHEN t.t_15 IS NOT NULL THEN 22
                            WHEN t.t_14 IS NOT NULL THEN 23
                            WHEN t.t_13 IS NOT NULL THEN 24
                            WHEN t.t_12 IS NOT NULL THEN 25
                            WHEN t.t_11 IS NOT NULL THEN 26
                            WHEN t.t_10 IS NOT NULL THEN 27
                            WHEN t.t_9 IS NOT NULL THEN 28
                            WHEN t.t_8 IS NOT NULL THEN 29
                            WHEN t.t_7 IS NOT NULL THEN 30
                            WHEN t.t_6 IS NOT NULL THEN 31
                            WHEN t.t_5 IS NOT NULL THEN 32
                            WHEN t.t_4 IS NOT NULL THEN 33
                            WHEN t.t_3 IS NOT NULL THEN 34
                            WHEN t.t_2 IS NOT NULL THEN 35
                            WHEN t.t_1 IS NOT NULL THEN 36
                        END
                    ) IS NULL THEN NULL
                    ELSE
                        (
                            COALESCE(t.t_36,0) + COALESCE(t.t_35,0) + COALESCE(t.t_34,0) + COALESCE(t.t_33,0)
                          + COALESCE(t.t_32,0) + COALESCE(t.t_31,0) + COALESCE(t.t_30,0) + COALESCE(t.t_29,0)
                          + COALESCE(t.t_28,0) + COALESCE(t.t_27,0) + COALESCE(t.t_26,0) + COALESCE(t.t_25,0)
                          + COALESCE(t.t_24,0) + COALESCE(t.t_23,0) + COALESCE(t.t_22,0) + COALESCE(t.t_21,0)
                          + COALESCE(t.t_20,0) + COALESCE(t.t_19,0) + COALESCE(t.t_18,0) + COALESCE(t.t_17,0)
                          + COALESCE(t.t_16,0) + COALESCE(t.t_15,0) + COALESCE(t.t_14,0) + COALESCE(t.t_13,0)
                          + COALESCE(t.t_12,0) + COALESCE(t.t_11,0) + COALESCE(t.t_10,0) + COALESCE(t.t_9,0)
                          + COALESCE(t.t_8,0)  + COALESCE(t.t_7,0)  + COALESCE(t.t_6,0)  + COALESCE(t.t_5,0)
                          + COALESCE(t.t_4,0)  + COALESCE(t.t_3,0)  + COALESCE(t.t_2,0)  + COALESCE(t.t_1,0)
                        )::NUMERIC(10,4)
                        /
                        (
                            (
                                CASE
                                    WHEN t.t_1 IS NOT NULL THEN 36
                                    WHEN t.t_2 IS NOT NULL THEN 35
                                    WHEN t.t_3 IS NOT NULL THEN 34
                                    WHEN t.t_4 IS NOT NULL THEN 33
                                    WHEN t.t_5 IS NOT NULL THEN 32
                                    WHEN t.t_6 IS NOT NULL THEN 31
                                    WHEN t.t_7 IS NOT NULL THEN 30
                                    WHEN t.t_8 IS NOT NULL THEN 29
                                    WHEN t.t_9 IS NOT NULL THEN 28
                                    WHEN t.t_10 IS NOT NULL THEN 27
                                    WHEN t.t_11 IS NOT NULL THEN 26
                                    WHEN t.t_12 IS NOT NULL THEN 25
                                    WHEN t.t_13 IS NOT NULL THEN 24
                                    WHEN t.t_14 IS NOT NULL THEN 23
                                    WHEN t.t_15 IS NOT NULL THEN 22
                                    WHEN t.t_16 IS NOT NULL THEN 21
                                    WHEN t.t_17 IS NOT NULL THEN 20
                                    WHEN t.t_18 IS NOT NULL THEN 19
                                    WHEN t.t_19 IS NOT NULL THEN 18
                                    WHEN t.t_20 IS NOT NULL THEN 17
                                    WHEN t.t_21 IS NOT NULL THEN 16
                                    WHEN t.t_22 IS NOT NULL THEN 15
                                    WHEN t.t_23 IS NOT NULL THEN 14
                                    WHEN t.t_24 IS NOT NULL THEN 13
                                    WHEN t.t_25 IS NOT NULL THEN 12
                                    WHEN t.t_26 IS NOT NULL THEN 11
                                    WHEN t.t_27 IS NOT NULL THEN 10
                                    WHEN t.t_28 IS NOT NULL THEN 9
                                    WHEN t.t_29 IS NOT NULL THEN 8
                                    WHEN t.t_30 IS NOT NULL THEN 7
                                    WHEN t.t_31 IS NOT NULL THEN 6
                                    WHEN t.t_32 IS NOT NULL THEN 5
                                    WHEN t.t_33 IS NOT NULL THEN 4
                                    WHEN t.t_34 IS NOT NULL THEN 3
                                    WHEN t.t_35 IS NOT NULL THEN 2
                                    WHEN t.t_36 IS NOT NULL THEN 1
                                END
                            )
                            -
                            (
                                CASE
                                    WHEN t.t_36 IS NOT NULL THEN 1
                                    WHEN t.t_35 IS NOT NULL THEN 2
                                    WHEN t.t_34 IS NOT NULL THEN 3
                                    WHEN t.t_33 IS NOT NULL THEN 4
                                    WHEN t.t_32 IS NOT NULL THEN 5
                                    WHEN t.t_31 IS NOT NULL THEN 6
                                    WHEN t.t_30 IS NOT NULL THEN 7
                                    WHEN t.t_29 IS NOT NULL THEN 8
                                    WHEN t.t_28 IS NOT NULL THEN 9
                                    WHEN t.t_27 IS NOT NULL THEN 10
                                    WHEN t.t_26 IS NOT NULL THEN 11
                                    WHEN t.t_25 IS NOT NULL THEN 12
                                    WHEN t.t_24 IS NOT NULL THEN 13
                                    WHEN t.t_23 IS NOT NULL THEN 14
                                    WHEN t.t_22 IS NOT NULL THEN 15
                                    WHEN t.t_21 IS NOT NULL THEN 16
                                    WHEN t.t_20 IS NOT NULL THEN 17
                                    WHEN t.t_19 IS NOT NULL THEN 18
                                    WHEN t.t_18 IS NOT NULL THEN 19
                                    WHEN t.t_17 IS NOT NULL THEN 20
                                    WHEN t.t_16 IS NOT NULL THEN 21
                                    WHEN t.t_15 IS NOT NULL THEN 22
                                    WHEN t.t_14 IS NOT NULL THEN 23
                                    WHEN t.t_13 IS NOT NULL THEN 24
                                    WHEN t.t_12 IS NOT NULL THEN 25
                                    WHEN t.t_11 IS NOT NULL THEN 26
                                    WHEN t.t_10 IS NOT NULL THEN 27
                                    WHEN t.t_9 IS NOT NULL THEN 28
                                    WHEN t.t_8 IS NOT NULL THEN 29
                                    WHEN t.t_7 IS NOT NULL THEN 30
                                    WHEN t.t_6 IS NOT NULL THEN 31
                                    WHEN t.t_5 IS NOT NULL THEN 32
                                    WHEN t.t_4 IS NOT NULL THEN 33
                                    WHEN t.t_3 IS NOT NULL THEN 34
                                    WHEN t.t_2 IS NOT NULL THEN 35
                                    WHEN t.t_1 IS NOT NULL THEN 36
                                END
                            )
                            + 1
                        )
                END
            ) AS avg_dpd_l36m
     from PP_HS_BASE_BU_TL_5 t;""")


    duckdb.sql("""create table PP_HS_BASE_BU_TL_7 as
    select *,
    -- ================== recency_wtd_avg_dpd_l3m (t_3..t_1) ==================
            CASE
                WHEN t.t_1 IS NULL AND t.t_2 IS NULL AND t.t_3 IS NULL THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1 IS NOT NULL THEN t.t_1 * ((3-0)/3) ELSE 0 END) +
                        (CASE WHEN t.t_2 IS NOT NULL THEN t.t_2 * ((3-1)/3) ELSE 0 END) +
                        (CASE WHEN t.t_3 IS NOT NULL THEN t.t_3 * ((3-2)/3) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1 IS NOT NULL THEN ((3-0)/3) ELSE 0 END) +
                        (CASE WHEN t.t_2 IS NOT NULL THEN ((3-1)/3) ELSE 0 END) +
                        (CASE WHEN t.t_3 IS NOT NULL THEN ((3-2)/3) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l3m,
    
            -- ================== recency_wtd_avg_dpd_l6m (t_6..t_1) ==================
            CASE
                WHEN t.t_1 IS NULL AND t.t_2 IS NULL AND t.t_3 IS NULL
                 AND t.t_4 IS NULL AND t.t_5 IS NULL AND t.t_6 IS NULL THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1 IS NOT NULL THEN t.t_1 * ((6-0)/6) ELSE 0 END) +
                        (CASE WHEN t.t_2 IS NOT NULL THEN t.t_2 * ((6-1)/6) ELSE 0 END) +
                        (CASE WHEN t.t_3 IS NOT NULL THEN t.t_3 * ((6-2)/6) ELSE 0 END) +
                        (CASE WHEN t.t_4 IS NOT NULL THEN t.t_4 * ((6-3)/6) ELSE 0 END) +
                        (CASE WHEN t.t_5 IS NOT NULL THEN t.t_5 * ((6-4)/6) ELSE 0 END) +
                        (CASE WHEN t.t_6 IS NOT NULL THEN t.t_6 * ((6-5)/6) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1 IS NOT NULL THEN ((6-0)/6) ELSE 0 END) +
                        (CASE WHEN t.t_2 IS NOT NULL THEN ((6-1)/6) ELSE 0 END) +
                        (CASE WHEN t.t_3 IS NOT NULL THEN ((6-2)/6) ELSE 0 END) +
                        (CASE WHEN t.t_4 IS NOT NULL THEN ((6-3)/6) ELSE 0 END) +
                        (CASE WHEN t.t_5 IS NOT NULL THEN ((6-4)/6) ELSE 0 END) +
                        (CASE WHEN t.t_6 IS NOT NULL THEN ((6-5)/6) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l6m,
    
            -- ================== recency_wtd_avg_dpd_l9m (t_9..t_1) ==================
            CASE
                WHEN t.t_1 IS NULL AND t.t_2 IS NULL AND t.t_3 IS NULL
                 AND t.t_4 IS NULL AND t.t_5 IS NULL AND t.t_6 IS NULL
                 AND t.t_7 IS NULL AND t.t_8 IS NULL AND t.t_9 IS NULL THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1 IS NOT NULL THEN t.t_1 * ((9-0)/9) ELSE 0 END) +
                        (CASE WHEN t.t_2 IS NOT NULL THEN t.t_2 * ((9-1)/9) ELSE 0 END) +
                        (CASE WHEN t.t_3 IS NOT NULL THEN t.t_3 * ((9-2)/9) ELSE 0 END) +
                        (CASE WHEN t.t_4 IS NOT NULL THEN t.t_4 * ((9-3)/9) ELSE 0 END) +
                        (CASE WHEN t.t_5 IS NOT NULL THEN t.t_5 * ((9-4)/9) ELSE 0 END) +
                        (CASE WHEN t.t_6 IS NOT NULL THEN t.t_6 * ((9-5)/9) ELSE 0 END) +
                        (CASE WHEN t.t_7 IS NOT NULL THEN t.t_7 * ((9-6)/9) ELSE 0 END) +
                        (CASE WHEN t.t_8 IS NOT NULL THEN t.t_8 * ((9-7)/9) ELSE 0 END) +
                        (CASE WHEN t.t_9 IS NOT NULL THEN t.t_9 * ((9-8)/9) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1 IS NOT NULL THEN ((9-0)/9) ELSE 0 END) +
                        (CASE WHEN t.t_2 IS NOT NULL THEN ((9-1)/9) ELSE 0 END) +
                        (CASE WHEN t.t_3 IS NOT NULL THEN ((9-2)/9) ELSE 0 END) +
                        (CASE WHEN t.t_4 IS NOT NULL THEN ((9-3)/9) ELSE 0 END) +
                        (CASE WHEN t.t_5 IS NOT NULL THEN ((9-4)/9) ELSE 0 END) +
                        (CASE WHEN t.t_6 IS NOT NULL THEN ((9-5)/9) ELSE 0 END) +
                        (CASE WHEN t.t_7 IS NOT NULL THEN ((9-6)/9) ELSE 0 END) +
                        (CASE WHEN t.t_8 IS NOT NULL THEN ((9-7)/9) ELSE 0 END) +
                        (CASE WHEN t.t_9 IS NOT NULL THEN ((9-8)/9) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l9m,
    
            -- ================== recency_wtd_avg_dpd_l12m (t_12..t_1) ==================
            CASE
                WHEN t.t_1  IS NULL AND t.t_2  IS NULL AND t.t_3  IS NULL AND t.t_4  IS NULL
                 AND t.t_5  IS NULL AND t.t_6  IS NULL AND t.t_7  IS NULL AND t.t_8  IS NULL
                 AND t.t_9  IS NULL AND t.t_10 IS NULL AND t.t_11 IS NULL AND t.t_12 IS NULL
                THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1  IS NOT NULL THEN t.t_1  * ((12-0)/12) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN t.t_2  * ((12-1)/12) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN t.t_3  * ((12-2)/12) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN t.t_4  * ((12-3)/12) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN t.t_5  * ((12-4)/12) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN t.t_6  * ((12-5)/12) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN t.t_7  * ((12-6)/12) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN t.t_8  * ((12-7)/12) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN t.t_9  * ((12-8)/12) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN t.t_10 * ((12-9)/12) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN t.t_11 * ((12-10)/12) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN t.t_12 * ((12-11)/12) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1  IS NOT NULL THEN ((12-0)/12) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN ((12-1)/12) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN ((12-2)/12) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN ((12-3)/12) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN ((12-4)/12) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN ((12-5)/12) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN ((12-6)/12) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN ((12-7)/12) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN ((12-8)/12) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN ((12-9)/12) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN ((12-10)/12) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN ((12-11)/12) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l12m,
    
            -- ================== recency_wtd_avg_dpd_l18m (t_18..t_1) ==================
            CASE
                WHEN t.t_1  IS NULL AND t.t_2  IS NULL AND t.t_3  IS NULL AND t.t_4  IS NULL
                 AND t.t_5  IS NULL AND t.t_6  IS NULL AND t.t_7  IS NULL AND t.t_8  IS NULL
                 AND t.t_9  IS NULL AND t.t_10 IS NULL AND t.t_11 IS NULL AND t.t_12 IS NULL
                 AND t.t_13 IS NULL AND t.t_14 IS NULL AND t.t_15 IS NULL AND t.t_16 IS NULL
                 AND t.t_17 IS NULL AND t.t_18 IS NULL
                THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1  IS NOT NULL THEN t.t_1  * ((18-0)/18) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN t.t_2  * ((18-1)/18) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN t.t_3  * ((18-2)/18) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN t.t_4  * ((18-3)/18) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN t.t_5  * ((18-4)/18) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN t.t_6  * ((18-5)/18) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN t.t_7  * ((18-6)/18) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN t.t_8  * ((18-7)/18) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN t.t_9  * ((18-8)/18) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN t.t_10 * ((18-9)/18) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN t.t_11 * ((18-10)/18) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN t.t_12 * ((18-11)/18) ELSE 0 END) +
                        (CASE WHEN t.t_13 IS NOT NULL THEN t.t_13 * ((18-12)/18) ELSE 0 END) +
                        (CASE WHEN t.t_14 IS NOT NULL THEN t.t_14 * ((18-13)/18) ELSE 0 END) +
                        (CASE WHEN t.t_15 IS NOT NULL THEN t.t_15 * ((18-14)/18) ELSE 0 END) +
                        (CASE WHEN t.t_16 IS NOT NULL THEN t.t_16 * ((18-15)/18) ELSE 0 END) +
                        (CASE WHEN t.t_17 IS NOT NULL THEN t.t_17 * ((18-16)/18) ELSE 0 END) +
                        (CASE WHEN t.t_18 IS NOT NULL THEN t.t_18 * ((18-17)/18) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1  IS NOT NULL THEN ((18-0)/18) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN ((18-1)/18) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN ((18-2)/18) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN ((18-3)/18) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN ((18-4)/18) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN ((18-5)/18) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN ((18-6)/18) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN ((18-7)/18) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN ((18-8)/18) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN ((18-9)/18) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN ((18-10)/18) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN ((18-11)/18) ELSE 0 END) +
                        (CASE WHEN t.t_13 IS NOT NULL THEN ((18-12)/18) ELSE 0 END) +
                        (CASE WHEN t.t_14 IS NOT NULL THEN ((18-13)/18) ELSE 0 END) +
                        (CASE WHEN t.t_15 IS NOT NULL THEN ((18-14)/18) ELSE 0 END) +
                        (CASE WHEN t.t_16 IS NOT NULL THEN ((18-15)/18) ELSE 0 END) +
                        (CASE WHEN t.t_17 IS NOT NULL THEN ((18-16)/18) ELSE 0 END) +
                        (CASE WHEN t.t_18 IS NOT NULL THEN ((18-17)/18) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l18m,
-- ================== recency_wtd_avg_dpd_l24m (t_24..t_1) ==================
            CASE
                WHEN t.t_1  IS NULL AND t.t_2  IS NULL AND t.t_3  IS NULL AND t.t_4  IS NULL
                 AND t.t_5  IS NULL AND t.t_6  IS NULL AND t.t_7  IS NULL AND t.t_8  IS NULL
                 AND t.t_9  IS NULL AND t.t_10 IS NULL AND t.t_11 IS NULL AND t.t_12 IS NULL
                 AND t.t_13 IS NULL AND t.t_14 IS NULL AND t.t_15 IS NULL AND t.t_16 IS NULL
                 AND t.t_17 IS NULL AND t.t_18 IS NULL AND t.t_19 IS NULL AND t.t_20 IS NULL
                 AND t.t_21 IS NULL AND t.t_22 IS NULL AND t.t_23 IS NULL AND t.t_24 IS NULL
                THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1  IS NOT NULL THEN t.t_1  * ((24-0)/24) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN t.t_2  * ((24-1)/24) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN t.t_3  * ((24-2)/24) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN t.t_4  * ((24-3)/24) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN t.t_5  * ((24-4)/24) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN t.t_6  * ((24-5)/24) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN t.t_7  * ((24-6)/24) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN t.t_8  * ((24-7)/24) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN t.t_9  * ((24-8)/24) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN t.t_10 * ((24-9)/24) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN t.t_11 * ((24-10)/24) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN t.t_12 * ((24-11)/24) ELSE 0 END) +
                        (CASE WHEN t.t_13 IS NOT NULL THEN t.t_13 * ((24-12)/24) ELSE 0 END) +
                        (CASE WHEN t.t_14 IS NOT NULL THEN t.t_14 * ((24-13)/24) ELSE 0 END) +
                        (CASE WHEN t.t_15 IS NOT NULL THEN t.t_15 * ((24-14)/24) ELSE 0 END) +
                        (CASE WHEN t.t_16 IS NOT NULL THEN t.t_16 * ((24-15)/24) ELSE 0 END) +
                        (CASE WHEN t.t_17 IS NOT NULL THEN t.t_17 * ((24-16)/24) ELSE 0 END) +
                        (CASE WHEN t.t_18 IS NOT NULL THEN t.t_18 * ((24-17)/24) ELSE 0 END) +
                        (CASE WHEN t.t_19 IS NOT NULL THEN t.t_19 * ((24-18)/24) ELSE 0 END) +
                        (CASE WHEN t.t_20 IS NOT NULL THEN t.t_20 * ((24-19)/24) ELSE 0 END) +
                        (CASE WHEN t.t_21 IS NOT NULL THEN t.t_21 * ((24-20)/24) ELSE 0 END) +
                        (CASE WHEN t.t_22 IS NOT NULL THEN t.t_22 * ((24-21)/24) ELSE 0 END) +
                        (CASE WHEN t.t_23 IS NOT NULL THEN t.t_23 * ((24-22)/24) ELSE 0 END) +
                        (CASE WHEN t.t_24 IS NOT NULL THEN t.t_24 * ((24-23)/24) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1  IS NOT NULL THEN ((24-0)/24) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN ((24-1)/24) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN ((24-2)/24) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN ((24-3)/24) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN ((24-4)/24) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN ((24-5)/24) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN ((24-6)/24) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN ((24-7)/24) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN ((24-8)/24) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN ((24-9)/24) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN ((24-10)/24) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN ((24-11)/24) ELSE 0 END) +
                        (CASE WHEN t.t_13 IS NOT NULL THEN ((24-12)/24) ELSE 0 END) +
                        (CASE WHEN t.t_14 IS NOT NULL THEN ((24-13)/24) ELSE 0 END) +
                        (CASE WHEN t.t_15 IS NOT NULL THEN ((24-14)/24) ELSE 0 END) +
                        (CASE WHEN t.t_16 IS NOT NULL THEN ((24-15)/24) ELSE 0 END) +
                        (CASE WHEN t.t_17 IS NOT NULL THEN ((24-16)/24) ELSE 0 END) +
                        (CASE WHEN t.t_18 IS NOT NULL THEN ((24-17)/24) ELSE 0 END) +
                        (CASE WHEN t.t_19 IS NOT NULL THEN ((24-18)/24) ELSE 0 END) +
                        (CASE WHEN t.t_20 IS NOT NULL THEN ((24-19)/24) ELSE 0 END) +
                        (CASE WHEN t.t_21 IS NOT NULL THEN ((24-20)/24) ELSE 0 END) +
                        (CASE WHEN t.t_22 IS NOT NULL THEN ((24-21)/24) ELSE 0 END) +
                        (CASE WHEN t.t_23 IS NOT NULL THEN ((24-22)/24) ELSE 0 END) +
                        (CASE WHEN t.t_24 IS NOT NULL THEN ((24-23)/24) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l24m,
    
            -- ================== recency_wtd_avg_dpd_l36m (t_36..t_1) ==================
            CASE
                WHEN t.t_1  IS NULL AND t.t_2  IS NULL AND t.t_3  IS NULL AND t.t_4  IS NULL
                 AND t.t_5  IS NULL AND t.t_6  IS NULL AND t.t_7  IS NULL AND t.t_8  IS NULL
                 AND t.t_9  IS NULL AND t.t_10 IS NULL AND t.t_11 IS NULL AND t.t_12 IS NULL
                 AND t.t_13 IS NULL AND t.t_14 IS NULL AND t.t_15 IS NULL AND t.t_16 IS NULL
                 AND t.t_17 IS NULL AND t.t_18 IS NULL AND t.t_19 IS NULL AND t.t_20 IS NULL
                 AND t.t_21 IS NULL AND t.t_22 IS NULL AND t.t_23 IS NULL AND t.t_24 IS NULL
                 AND t.t_25 IS NULL AND t.t_26 IS NULL AND t.t_27 IS NULL AND t.t_28 IS NULL
                 AND t.t_29 IS NULL AND t.t_30 IS NULL AND t.t_31 IS NULL AND t.t_32 IS NULL
                 AND t.t_33 IS NULL AND t.t_34 IS NULL AND t.t_35 IS NULL AND t.t_36 IS NULL
                THEN NULL
                ELSE
                    (
                        (CASE WHEN t.t_1  IS NOT NULL THEN t.t_1  * ((36-0)/36) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN t.t_2  * ((36-1)/36) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN t.t_3  * ((36-2)/36) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN t.t_4  * ((36-3)/36) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN t.t_5  * ((36-4)/36) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN t.t_6  * ((36-5)/36) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN t.t_7  * ((36-6)/36) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN t.t_8  * ((36-7)/36) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN t.t_9  * ((36-8)/36) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN t.t_10 * ((36-9)/36) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN t.t_11 * ((36-10)/36) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN t.t_12 * ((36-11)/36) ELSE 0 END) +
                        (CASE WHEN t.t_13 IS NOT NULL THEN t.t_13 * ((36-12)/36) ELSE 0 END) +
                        (CASE WHEN t.t_14 IS NOT NULL THEN t.t_14 * ((36-13)/36) ELSE 0 END) +
                        (CASE WHEN t.t_15 IS NOT NULL THEN t.t_15 * ((36-14)/36) ELSE 0 END) +
                        (CASE WHEN t.t_16 IS NOT NULL THEN t.t_16 * ((36-15)/36) ELSE 0 END) +
                        (CASE WHEN t.t_17 IS NOT NULL THEN t.t_17 * ((36-16)/36) ELSE 0 END) +
                        (CASE WHEN t.t_18 IS NOT NULL THEN t.t_18 * ((36-17)/36) ELSE 0 END) +
                        (CASE WHEN t.t_19 IS NOT NULL THEN t.t_19 * ((36-18)/36) ELSE 0 END) +
                        (CASE WHEN t.t_20 IS NOT NULL THEN t.t_20 * ((36-19)/36) ELSE 0 END) +
                        (CASE WHEN t.t_21 IS NOT NULL THEN t.t_21 * ((36-20)/36) ELSE 0 END) +
                        (CASE WHEN t.t_22 IS NOT NULL THEN t.t_22 * ((36-21)/36) ELSE 0 END) +
                        (CASE WHEN t.t_23 IS NOT NULL THEN t.t_23 * ((36-22)/36) ELSE 0 END) +
                        (CASE WHEN t.t_24 IS NOT NULL THEN t.t_24 * ((36-23)/36) ELSE 0 END) +
                        (CASE WHEN t.t_25 IS NOT NULL THEN t.t_25 * ((36-24)/36) ELSE 0 END) +
                        (CASE WHEN t.t_26 IS NOT NULL THEN t.t_26 * ((36-25)/36) ELSE 0 END) +
                        (CASE WHEN t.t_27 IS NOT NULL THEN t.t_27 * ((36-26)/36) ELSE 0 END) +
                        (CASE WHEN t.t_28 IS NOT NULL THEN t.t_28 * ((36-27)/36) ELSE 0 END) +
                        (CASE WHEN t.t_29 IS NOT NULL THEN t.t_29 * ((36-28)/36) ELSE 0 END) +
                        (CASE WHEN t.t_30 IS NOT NULL THEN t.t_30 * ((36-29)/36) ELSE 0 END) +
                        (CASE WHEN t.t_31 IS NOT NULL THEN t.t_31 * ((36-30)/36) ELSE 0 END) +
                        (CASE WHEN t.t_32 IS NOT NULL THEN t.t_32 * ((36-31)/36) ELSE 0 END) +
                        (CASE WHEN t.t_33 IS NOT NULL THEN t.t_33 * ((36-32)/36) ELSE 0 END) +
                        (CASE WHEN t.t_34 IS NOT NULL THEN t.t_34 * ((36-33)/36) ELSE 0 END) +
                        (CASE WHEN t.t_35 IS NOT NULL THEN t.t_35 * ((36-34)/36) ELSE 0 END) +
                        (CASE WHEN t.t_36 IS NOT NULL THEN t.t_36 * ((36-35)/36) ELSE 0 END)
                    )
                    /
                    NULLIF(
                        (CASE WHEN t.t_1  IS NOT NULL THEN ((36-0)/36) ELSE 0 END) +
                        (CASE WHEN t.t_2  IS NOT NULL THEN ((36-1)/36) ELSE 0 END) +
                        (CASE WHEN t.t_3  IS NOT NULL THEN ((36-2)/36) ELSE 0 END) +
                        (CASE WHEN t.t_4  IS NOT NULL THEN ((36-3)/36) ELSE 0 END) +
                        (CASE WHEN t.t_5  IS NOT NULL THEN ((36-4)/36) ELSE 0 END) +
                        (CASE WHEN t.t_6  IS NOT NULL THEN ((36-5)/36) ELSE 0 END) +
                        (CASE WHEN t.t_7  IS NOT NULL THEN ((36-6)/36) ELSE 0 END) +
                        (CASE WHEN t.t_8  IS NOT NULL THEN ((36-7)/36) ELSE 0 END) +
                        (CASE WHEN t.t_9  IS NOT NULL THEN ((36-8)/36) ELSE 0 END) +
                        (CASE WHEN t.t_10 IS NOT NULL THEN ((36-9)/36) ELSE 0 END) +
                        (CASE WHEN t.t_11 IS NOT NULL THEN ((36-10)/36) ELSE 0 END) +
                        (CASE WHEN t.t_12 IS NOT NULL THEN ((36-11)/36) ELSE 0 END) +
                        (CASE WHEN t.t_13 IS NOT NULL THEN ((36-12)/36) ELSE 0 END) +
                        (CASE WHEN t.t_14 IS NOT NULL THEN ((36-13)/36) ELSE 0 END) +
                        (CASE WHEN t.t_15 IS NOT NULL THEN ((36-14)/36) ELSE 0 END) +
                        (CASE WHEN t.t_16 IS NOT NULL THEN ((36-15)/36) ELSE 0 END) +
                        (CASE WHEN t.t_17 IS NOT NULL THEN ((36-16)/36) ELSE 0 END) +
                        (CASE WHEN t.t_18 IS NOT NULL THEN ((36-17)/36) ELSE 0 END) +
                        (CASE WHEN t.t_19 IS NOT NULL THEN ((36-18)/36) ELSE 0 END) +
                        (CASE WHEN t.t_20 IS NOT NULL THEN ((36-19)/36) ELSE 0 END) +
                        (CASE WHEN t.t_21 IS NOT NULL THEN ((36-20)/36) ELSE 0 END) +
                        (CASE WHEN t.t_22 IS NOT NULL THEN ((36-21)/36) ELSE 0 END) +
                        (CASE WHEN t.t_23 IS NOT NULL THEN ((36-22)/36) ELSE 0 END) +
                        (CASE WHEN t.t_24 IS NOT NULL THEN ((36-23)/36) ELSE 0 END) +
                        (CASE WHEN t.t_25 IS NOT NULL THEN ((36-24)/36) ELSE 0 END) +
                        (CASE WHEN t.t_26 IS NOT NULL THEN ((36-25)/36) ELSE 0 END) +
                        (CASE WHEN t.t_27 IS NOT NULL THEN ((36-26)/36) ELSE 0 END) +
                        (CASE WHEN t.t_28 IS NOT NULL THEN ((36-27)/36) ELSE 0 END) +
                        (CASE WHEN t.t_29 IS NOT NULL THEN ((36-28)/36) ELSE 0 END) +
                        (CASE WHEN t.t_30 IS NOT NULL THEN ((36-29)/36) ELSE 0 END) +
                        (CASE WHEN t.t_31 IS NOT NULL THEN ((36-30)/36) ELSE 0 END) +
                        (CASE WHEN t.t_32 IS NOT NULL THEN ((36-31)/36) ELSE 0 END) +
                        (CASE WHEN t.t_33 IS NOT NULL THEN ((36-32)/36) ELSE 0 END) +
                        (CASE WHEN t.t_34 IS NOT NULL THEN ((36-33)/36) ELSE 0 END) +
                        (CASE WHEN t.t_35 IS NOT NULL THEN ((36-34)/36) ELSE 0 END) +
                        (CASE WHEN t.t_36 IS NOT NULL THEN ((36-35)/36) ELSE 0 END),
                        0
                    )
            END AS recency_wtd_avg_dpd_l36m
     from PP_HS_BASE_BU_TL_6 t;
    
    
    alter table PP_HS_BASE_BU_TL_7 add column onus_flag integer;
    
    alter table PP_HS_BASE_BU_TL_7 add column f_all integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_lv integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_uns integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_sec integer;
    
    alter table PP_HS_BASE_BU_TL_7 add column f_pl integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_cc integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_bl integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_gl integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_hllap integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_hra integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_twl integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_cd integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_cons integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_plbl integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_onc integer;
    
    alter table PP_HS_BASE_BU_TL_7 add column f_exc_cc integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_exccgled integer;
    
    alter table PP_HS_BASE_BU_TL_7 add column f_allsal10k integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_allsal20k integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_allsal1l integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_allsag20k integer;
    alter table PP_HS_BASE_BU_TL_7 add column f_allsag1l integer;
    
    alter table PP_HS_BASE_BU_TL_7 add column age_trade decimal(10,2);
    
    update PP_HS_BASE_BU_TL_7
    set
        -- onus flag (same as your reference logic)
        onus_flag = case
            when sector in ('KOTAK BANK','KOTAK PRIME') then 1
            else 0
        end,
    
        -- /* ---------- PRODUCT FLAGS ---------- */
        f_all    = 1,
        f_cc     = case when account_type_cd in (10,16,31,35,36) then 1 else 0 end,
        f_exc_cc = case when account_type_cd not in (10,16,31,35,36) then 1 else 0 end,
        f_cd     = case when account_type_cd in (6) then 1 else 0 end,
        f_hra    = case when account_type_cd in (6,7,13) then 1 else 0 end,
        f_cons   = case when account_type_cd not in (1,17,33,8,2,42,3,34,13) then 1 else 0 end,
        f_plbl   = case when account_type_cd in (5,9,40,50,51,52,53,54,55,56,57,58,59,61,69) then 1 else 0 end,
        f_bl     = case when account_type_cd in (9,40,50,51,52,53,54,55,56,57,58,59,61) then 1 else 0 end,
        f_uns    = case when account_type_cd in (5,6,8,9,12,24,37,38,39,40,41,43,45,47,51,52,53,54,55,56,57,58,61,0,69,70,71) then 1 else 0 end,
        f_sec    = case when account_type_cd in (1,2,3,4,7,11,13,14,15,17,23,32,33,34,42,44,46,50,59) then 1 else 0 end,
        f_exccgled = case when account_type_cd not in (10,16,31,35,36,7,8) then 1 else 0 end,
        f_pl     = case when account_type_cd in (5,69) then 1 else 0 end,
        f_gl     = case when account_type_cd in (7) then 1 else 0 end,
        f_twl    = case when account_type_cd in (13) then 1 else 0 end,
        f_hllap  = case when account_type_cd in (2,3) then 1 else 0 end,
    
        -- /* ---------- SANCTION FLAGS (guard: sector not null) ---------- */
        f_allsag20k = case when is_sanc_amt_bel20k = 0 and sector is not null then 1 else 0 end,
        f_allsal20k = case when is_sanc_amt_bel20k = 1 and sector is not null then 1 else 0 end,
        f_allsag1l  = case when is_sanc_amt_bel1l  = 0 and sector is not null then 1 else 0 end,
        f_allsal10k = case when is_sanc_amt_bel10k = 1 and sector is not null then 1 else 0 end,
        f_allsal1l  = case when is_sanc_amt_bel1l  = 1 and sector is not null then 1 else 0 end,
    
        -- /* ---------- STATUS FLAGS ---------- */
        f_onc = case when open_flag is not null then 1 else 0 end,
        f_lv  = case when open_flag = 1 then 1 else 0 end,
    
        -- /* ---------- TRADE AGE (months, decimal) ---------- */
        age_trade = case
            when open_flag = 1 then greatest(round((date_diff('day', date_opened, scrub_date)::float) / 30.5, 2), 0)
            when open_flag = 0 then greatest(round((date_diff('day', date_opened, date_closed)::float) / 30.5, 2), 0)
            else null
        end
    ;
    
    create TEMP table PP_HS_BASE_BU_TL_8 as
    select *,
    case when t_1 is not null then 1 else 0 end as v_1,
    case when t_2 is not null then 1 else 0 end as v_2,
    case when t_3 is not null then 1 else 0 end as v_3,
    case when t_4 is not null then 1 else 0 end as v_4,
    case when t_5 is not null then 1 else 0 end as v_5,
    case when t_6 is not null then 1 else 0 end as v_6,
    case when t_7 is not null then 1 else 0 end as v_7,
    case when t_8 is not null then 1 else 0 end as v_8,
    case when t_9 is not null then 1 else 0 end as v_9,
    case when t_10 is not null then 1 else 0 end as v_10,
    case when t_11 is not null then 1 else 0 end as v_11,
    case when t_12 is not null then 1 else 0 end as v_12,
    case when t_13 is not null then 1 else 0 end as v_13,
    case when t_14 is not null then 1 else 0 end as v_14,
    case when t_15 is not null then 1 else 0 end as v_15,
    case when t_16 is not null then 1 else 0 end as v_16,
    case when t_17 is not null then 1 else 0 end as v_17,
    case when t_18 is not null then 1 else 0 end as v_18,
    case when t_19 is not null then 1 else 0 end as v_19,
    case when t_20 is not null then 1 else 0 end as v_20,
    case when t_21 is not null then 1 else 0 end as v_21,
    case when t_22 is not null then 1 else 0 end as v_22,
    case when t_23 is not null then 1 else 0 end as v_23,
    case when t_24 is not null then 1 else 0 end as v_24,
    case when t_25 is not null then 1 else 0 end as v_25,
    case when t_26 is not null then 1 else 0 end as v_26,
    case when t_27 is not null then 1 else 0 end as v_27,
    case when t_28 is not null then 1 else 0 end as v_28,
    case when t_29 is not null then 1 else 0 end as v_29,
    case when t_30 is not null then 1 else 0 end as v_30,
    case when t_31 is not null then 1 else 0 end as v_31,
    case when t_32 is not null then 1 else 0 end as v_32,
    case when t_33 is not null then 1 else 0 end as v_33,
    case when t_34 is not null then 1 else 0 end as v_34,
    case when t_35 is not null then 1 else 0 end as v_35,
    case when t_36 is not null then 1 else 0 end as v_36,
                 
    case when t_1>0 then 1 else 0 end as p_1,
    case when t_2>0 then 1 else 0 end as p_2,
    case when t_3>0 then 1 else 0 end as p_3,
    case when t_4>0 then 1 else 0 end as p_4,
    case when t_5>0 then 1 else 0 end as p_5,
    case when t_6>0 then 1 else 0 end as p_6,
    case when t_7>0 then 1 else 0 end as p_7,
    case when t_8>0 then 1 else 0 end as p_8,
    case when t_9>0 then 1 else 0 end as p_9,
    case when t_10>0 then 1 else 0 end as p_10,
    case when t_11>0 then 1 else 0 end as p_11,
    case when t_12>0 then 1 else 0 end as p_12,
    case when t_13>0 then 1 else 0 end as p_13,
    case when t_14>0 then 1 else 0 end as p_14,
    case when t_15>0 then 1 else 0 end as p_15,
    case when t_16>0 then 1 else 0 end as p_16,
    case when t_17>0 then 1 else 0 end as p_17,
    case when t_18>0 then 1 else 0 end as p_18,
    case when t_19>0 then 1 else 0 end as p_19,
    case when t_20>0 then 1 else 0 end as p_20,
    case when t_21>0 then 1 else 0 end as p_21,
    case when t_22>0 then 1 else 0 end as p_22,
    case when t_23>0 then 1 else 0 end as p_23,
    case when t_24>0 then 1 else 0 end as p_24,
    case when t_25>0 then 1 else 0 end as p_25,
    case when t_26>0 then 1 else 0 end as p_26,
    case when t_27>0 then 1 else 0 end as p_27,
    case when t_28>0 then 1 else 0 end as p_28,
    case when t_29>0 then 1 else 0 end as p_29,
    case when t_30>0 then 1 else 0 end as p_30,
    case when t_31>0 then 1 else 0 end as p_31,
    case when t_32>0 then 1 else 0 end as p_32,
    case when t_33>0 then 1 else 0 end as p_33,
    case when t_34>0 then 1 else 0 end as p_34,
    case when t_35>0 then 1 else 0 end as p_35,
    case when t_36>0 then 1 else 0 end as p_36,
    
    case when t_1>30 then 1 else 0 end as p30_1,
    case when t_2>30 then 1 else 0 end as p30_2,
    case when t_3>30 then 1 else 0 end as p30_3,
    case when t_4>30 then 1 else 0 end as p30_4,
    case when t_5>30 then 1 else 0 end as p30_5,
    case when t_6>30 then 1 else 0 end as p30_6,
    case when t_7>30 then 1 else 0 end as p30_7,
    case when t_8>30 then 1 else 0 end as p30_8,
    case when t_9>30 then 1 else 0 end as p30_9,
    case when t_10>30 then 1 else 0 end as p30_10,
    case when t_11>30 then 1 else 0 end as p30_11,
    case when t_12>30 then 1 else 0 end as p30_12,
    case when t_13>30 then 1 else 0 end as p30_13,
    case when t_14>30 then 1 else 0 end as p30_14,
    case when t_15>30 then 1 else 0 end as p30_15,
    case when t_16>30 then 1 else 0 end as p30_16,
    case when t_17>30 then 1 else 0 end as p30_17,
    case when t_18>30 then 1 else 0 end as p30_18,
    case when t_19>30 then 1 else 0 end as p30_19,
    case when t_20>30 then 1 else 0 end as p30_20,
    case when t_21>30 then 1 else 0 end as p30_21,
    case when t_22>30 then 1 else 0 end as p30_22,
    case when t_23>30 then 1 else 0 end as p30_23,
    case when t_24>30 then 1 else 0 end as p30_24,
    case when t_25>30 then 1 else 0 end as p30_25,
    case when t_26>30 then 1 else 0 end as p30_26,
    case when t_27>30 then 1 else 0 end as p30_27,
    case when t_28>30 then 1 else 0 end as p30_28,
    case when t_29>30 then 1 else 0 end as p30_29,
    case when t_30>30 then 1 else 0 end as p30_30,
    case when t_31>30 then 1 else 0 end as p30_31,
    case when t_32>30 then 1 else 0 end as p30_32,
    case when t_33>30 then 1 else 0 end as p30_33,
    case when t_34>30 then 1 else 0 end as p30_34,
    case when t_35>30 then 1 else 0 end as p30_35,
    case when t_36>30 then 1 else 0 end as p30_36,
                              
    case
        when t_1 is null then null
        when t_2 is null and t_1 > 0 then 1
        when t_2 is not null and (t_1 - t_2) > 5 then 1
        else 0
    end as mp_1,
    case
        when t_2 is null then null
        when t_3 is null and t_2 > 0 then 1
        when t_3 is not null and (t_2 - t_3) > 5 then 1
        else 0
    end as mp_2,
    case
        when t_3 is null then null
        when t_4 is null and t_3 > 0 then 1
        when t_4 is not null and (t_3 - t_4) > 5 then 1
        else 0
    end as mp_3,
    case
        when t_4 is null then null
        when t_5 is null and t_4 > 0 then 1
        when t_5 is not null and (t_4 - t_5) > 5 then 1
        else 0
    end as mp_4,
    case
        when t_5 is null then null
        when t_6 is null and t_5 > 0 then 1
        when t_6 is not null and (t_5 - t_6) > 5 then 1
        else 0
    end as mp_5,
    case
        when t_6 is null then null
        when t_7 is null and t_6 > 0 then 1
        when t_7 is not null and (t_6 - t_7) > 5 then 1
        else 0
    end as mp_6,
    case
        when t_7 is null then null
        when t_8 is null and t_7 > 0 then 1
        when t_8 is not null and (t_7 - t_8) > 5 then 1
        else 0
    end as mp_7,
    case
        when t_8 is null then null
        when t_9 is null and t_8 > 0 then 1
        when t_9 is not null and (t_8 - t_9) > 5 then 1
        else 0
    end as mp_8,
    case
        when t_9 is null then null
        when t_10 is null and t_9 > 0 then 1
        when t_10 is not null and (t_9 - t_10) > 5 then 1
        else 0
    end as mp_9,
    case
        when t_10 is null then null
        when t_11 is null and t_10 > 0 then 1
        when t_11 is not null and (t_10 - t_11) > 5 then 1
        else 0
    end as mp_10,
    case
        when t_11 is null then null
        when t_12 is null and t_11 > 0 then 1
        when t_12 is not null and (t_11 - t_12) > 5 then 1
        else 0
    end as mp_11,
    case
        when t_12 is null then null
        when t_13 is null and t_12 > 0 then 1
        when t_13 is not null and (t_12 - t_13) > 5 then 1
        else 0
    end as mp_12,
    case
        when t_13 is null then null
        when t_14 is null and t_13 > 0 then 1
        when t_14 is not null and (t_13 - t_14) > 5 then 1
        else 0
    end as mp_13,
    case
        when t_14 is null then null
        when t_15 is null and t_14 > 0 then 1
        when t_15 is not null and (t_14 - t_15) > 5 then 1
        else 0
    end as mp_14,
    case
        when t_15 is null then null
        when t_16 is null and t_15 > 0 then 1
        when t_16 is not null and (t_15 - t_16) > 5 then 1
        else 0
    end as mp_15,
    case
        when t_16 is null then null
        when t_17 is null and t_16 > 0 then 1
        when t_17 is not null and (t_16 - t_17) > 5 then 1
        else 0
    end as mp_16,
    case
        when t_17 is null then null
        when t_18 is null and t_17 > 0 then 1
        when t_18 is not null and (t_17 - t_18) > 5 then 1
        else 0
    end as mp_17,
    case
        when t_18 is null then null
        when t_19 is null and t_18 > 0 then 1
        when t_19 is not null and (t_18 - t_19) > 5 then 1
        else 0
    end as mp_18,
    case
        when t_19 is null then null
        when t_20 is null and t_19 > 0 then 1
        when t_20 is not null and (t_19 - t_20) > 5 then 1
        else 0
    end as mp_19,
    case
        when t_20 is null then null
        when t_21 is null and t_20 > 0 then 1
        when t_21 is not null and (t_20 - t_21) > 5 then 1
        else 0
    end as mp_20,
    case
        when t_21 is null then null
        when t_22 is null and t_21 > 0 then 1
        when t_22 is not null and (t_21 - t_22) > 5 then 1
        else 0
    end as mp_21,
    case
        when t_22 is null then null
        when t_23 is null and t_22 > 0 then 1
        when t_23 is not null and (t_22 - t_23) > 5 then 1
        else 0
    end as mp_22,
    case
        when t_23 is null then null
        when t_24 is null and t_23 > 0 then 1
        when t_24 is not null and (t_23 - t_24) > 5 then 1
        else 0
    end as mp_23,
    case
        when t_24 is null then null
        when t_25 is null and t_24 > 0 then 1
        when t_25 is not null and (t_24 - t_25) > 5 then 1
        else 0
    end as mp_24,
    case
        when t_25 is null then null
        when t_26 is null and t_25 > 0 then 1
        when t_26 is not null and (t_25 - t_26) > 5 then 1
        else 0
    end as mp_25,
    case
        when t_26 is null then null
        when t_27 is null and t_26 > 0 then 1
        when t_27 is not null and (t_26 - t_27) > 5 then 1
        else 0
    end as mp_26,
    case
        when t_27 is null then null
        when t_28 is null and t_27 > 0 then 1
        when t_28 is not null and (t_27 - t_28) > 5 then 1
        else 0
    end as mp_27,
    case
        when t_28 is null then null
        when t_29 is null and t_28 > 0 then 1
        when t_29 is not null and (t_28 - t_29) > 5 then 1
        else 0
    end as mp_28,
    case
        when t_29 is null then null
        when t_30 is null and t_29 > 0 then 1
        when t_30 is not null and (t_29 - t_30) > 5 then 1
        else 0
    end as mp_29,
    case
        when t_30 is null then null
        when t_31 is null and t_30 > 0 then 1
        when t_31 is not null and (t_30 - t_31) > 5 then 1
        else 0
    end as mp_30,
    case
        when t_31 is null then null
        when t_32 is null and t_31 > 0 then 1
        when t_32 is not null and (t_31 - t_32) > 5 then 1
        else 0
    end as mp_31,
    case
        when t_32 is null then null
        when t_33 is null and t_32 > 0 then 1
        when t_33 is not null and (t_32 - t_33) > 5 then 1
        else 0
    end as mp_32,
    case
        when t_33 is null then null
        when t_34 is null and t_33 > 0 then 1
        when t_34 is not null and (t_33 - t_34) > 5 then 1
        else 0
    end as mp_33,
    case
        when t_34 is null then null
        when t_35 is null and t_34 > 0 then 1
        when t_35 is not null and (t_34 - t_35) > 5 then 1
        else 0
    end as mp_34,
    case
        when t_35 is null then null
        when t_36 is null and t_35 > 0 then 1
        when t_36 is not null and (t_35 - t_36) > 5 then 1
        else 0
    end as mp_35,
    
    case
        when t_36 is null then null
        when t_36 > 0 then 1
        else 0
    end as mp_36
     from PP_HS_BASE_BU_TL_7;
    
    create table PP_HS_BASE_BU_TL_9 as
    select *,
    v_1+v_2+v_3 as valid_pymt_cnt_last3m,
    p_1+p_2+p_3 as cnt_0p_last3m,
    p30_1+p30_2+p30_3 as cnt_30p_last3m,
           case
        when mp_1 is null and mp_2 is null and mp_3 is null then null
        else coalesce(mp_1,0) + coalesce(mp_2,0) + coalesce(mp_3,0)
    end as missed_pymt_cnt_last3m,
    
    valid_pymt_cnt_last3m + v_4 + v_5 + v_6 as valid_pymt_cnt_last6m,
    
    	cnt_0p_last3m + p_4 + p_5 + p_6 as cnt_0p_last6m,
    cnt_30p_last3m + p30_4 + p30_5 + p30_6 as cnt_30p_last6m,
    
    	 case
        when missed_pymt_cnt_last3m is null and mp_4 is null and mp_5 is null and mp_6 is null then null
        else coalesce(missed_pymt_cnt_last3m,0) + coalesce(mp_4,0) + coalesce(mp_5,0) + coalesce(mp_6,0)
    end as missed_pymt_cnt_last6m,
    
    (valid_pymt_cnt_last6m
                + COALESCE(v_7, 0) + COALESCE(v_8, 0) + COALESCE(v_9, 0))
                AS valid_pymt_cnt_last9m,
    
          
            (cnt_0p_last6m
                + COALESCE(p_7, 0) + COALESCE(p_8, 0) + COALESCE(p_9, 0))
                AS cnt_0p_last9m,
    
     (cnt_30p_last6m
                + COALESCE(p30_7, 0) + COALESCE(p30_8, 0) + COALESCE(p30_9, 0))
                AS cnt_30p_last9m,
    
     
            CASE
                WHEN missed_pymt_cnt_last6m IS NULL
                     AND mp_7 IS NULL AND mp_8 IS NULL AND mp_9 IS NULL
                THEN NULL
                ELSE COALESCE(missed_pymt_cnt_last6m, 0)
                     + COALESCE(mp_7, 0) + COALESCE(mp_8, 0) + COALESCE(mp_9, 0)
            END AS missed_pymt_cnt_last9m,
    
    (valid_pymt_cnt_last9m
                + COALESCE(v_10, 0) + COALESCE(v_11, 0) + COALESCE(v_12, 0))
                AS valid_pymt_cnt_last12m,
    
    
            (cnt_0p_last9m
                + COALESCE(p_10, 0) + COALESCE(p_11, 0) + COALESCE(p_12, 0))
                AS cnt_0p_last12m,
    
      (cnt_30p_last9m
                + COALESCE(p30_10, 0) + COALESCE(p30_11, 0) + COALESCE(p30_12, 0))
                AS cnt_30p_last12m,
    
         
            CASE
                WHEN missed_pymt_cnt_last9m IS NULL
                     AND mp_10 IS NULL AND mp_11 IS NULL AND mp_12 IS NULL
                THEN NULL
                ELSE COALESCE(missed_pymt_cnt_last9m, 0)
                     + COALESCE(mp_10, 0) + COALESCE(mp_11, 0) + COALESCE(mp_12, 0)
            END AS missed_pymt_cnt_last12m,
    
    (valid_pymt_cnt_last12m
                + COALESCE(v_13, 0) + COALESCE(v_14, 0) + COALESCE(v_15, 0)
                + COALESCE(v_16, 0) + COALESCE(v_17, 0) + COALESCE(v_18, 0))
                AS valid_pymt_cnt_last18m,
    
           
            (cnt_0p_last12m
                + COALESCE(p_13, 0) + COALESCE(p_14, 0) + COALESCE(p_15, 0)
                + COALESCE(p_16, 0) + COALESCE(p_17, 0) + COALESCE(p_18, 0))
                AS cnt_0p_last18m,
    
     (cnt_30p_last12m
                + COALESCE(p30_13, 0) + COALESCE(p30_14, 0) + COALESCE(p30_15, 0)
                + COALESCE(p30_16, 0) + COALESCE(p30_17, 0) + COALESCE(p30_18, 0))
                AS cnt_30p_last18m,
    
         
            CASE
                WHEN missed_pymt_cnt_last12m IS NULL
                     AND mp_13 IS NULL AND mp_14 IS NULL AND mp_15 IS NULL
                     AND mp_16 IS NULL AND mp_17 IS NULL AND mp_18 IS NULL
                THEN NULL
                ELSE COALESCE(missed_pymt_cnt_last12m, 0)
                     + COALESCE(mp_13, 0) + COALESCE(mp_14, 0) + COALESCE(mp_15, 0)
                     + COALESCE(mp_16, 0) + COALESCE(mp_17, 0) + COALESCE(mp_18, 0)
            END AS missed_pymt_cnt_last18m,
    
    (valid_pymt_cnt_last18m
                + COALESCE(v_19, 0) + COALESCE(v_20, 0) + COALESCE(v_21, 0)
                + COALESCE(v_22, 0) + COALESCE(v_23, 0) + COALESCE(v_24, 0))
                AS valid_pymt_cnt_last24m,
    
        
            (cnt_0p_last18m
                + COALESCE(p_19, 0) + COALESCE(p_20, 0) + COALESCE(p_21, 0)
                + COALESCE(p_22, 0) + COALESCE(p_23, 0) + COALESCE(p_24, 0))
                AS cnt_0p_last24m,
    
     (cnt_30p_last18m
                + COALESCE(p30_19, 0) + COALESCE(p30_20, 0) + COALESCE(p30_21, 0)
                + COALESCE(p30_22, 0) + COALESCE(p30_23, 0) + COALESCE(p30_24, 0))
                AS cnt_30p_last24m,
    
       
            CASE
                WHEN missed_pymt_cnt_last18m IS NULL
                     AND mp_19 IS NULL AND mp_20 IS NULL AND mp_21 IS NULL
                     AND mp_22 IS NULL AND mp_23 IS NULL AND mp_24 IS NULL
                THEN NULL
                ELSE COALESCE(missed_pymt_cnt_last18m, 0)
                     + COALESCE(mp_19, 0) + COALESCE(mp_20, 0) + COALESCE(mp_21, 0)
                     + COALESCE(mp_22, 0) + COALESCE(mp_23, 0) + COALESCE(mp_24, 0)
            END AS missed_pymt_cnt_last24m,
    
    (valid_pymt_cnt_last24m
                + COALESCE(v_25, 0) + COALESCE(v_26, 0) + COALESCE(v_27, 0)
                + COALESCE(v_28, 0) + COALESCE(v_29, 0) + COALESCE(v_30, 0)
                + COALESCE(v_31, 0) + COALESCE(v_32, 0) + COALESCE(v_33, 0)
                + COALESCE(v_34, 0) + COALESCE(v_35, 0) + COALESCE(v_36, 0))
                AS valid_pymt_cnt_last36m,
    
        
            (cnt_0p_last24m
                + COALESCE(p_25, 0) + COALESCE(p_26, 0) + COALESCE(p_27, 0)
                + COALESCE(p_28, 0) + COALESCE(p_29, 0) + COALESCE(p_30, 0)
                + COALESCE(p_31, 0) + COALESCE(p_32, 0) + COALESCE(p_33, 0)
                + COALESCE(p_34, 0) + COALESCE(p_35, 0) + COALESCE(p_36, 0))
                AS cnt_0p_last36m,
    
    
     (cnt_30p_last24m
                + COALESCE(p30_25, 0) + COALESCE(p30_26, 0) + COALESCE(p30_27, 0)
                + COALESCE(p30_28, 0) + COALESCE(p30_29, 0) + COALESCE(p30_30, 0)
                + COALESCE(p30_31, 0) + COALESCE(p30_32, 0) + COALESCE(p30_33, 0)
                + COALESCE(p30_34, 0) + COALESCE(p30_35, 0) + COALESCE(p30_36, 0))
                AS cnt_30p_last36m,
    
     
            CASE
                WHEN missed_pymt_cnt_last24m IS NULL
                     AND mp_25 IS NULL AND mp_26 IS NULL AND mp_27 IS NULL
                     AND mp_28 IS NULL AND mp_29 IS NULL AND mp_30 IS NULL
                     AND mp_31 IS NULL AND mp_32 IS NULL AND mp_33 IS NULL
                     AND mp_34 IS NULL AND mp_35 IS NULL AND mp_36 IS NULL
                THEN NULL
                ELSE COALESCE(missed_pymt_cnt_last24m, 0)
                     + COALESCE(mp_25, 0) + COALESCE(mp_26, 0) + COALESCE(mp_27, 0)
                     + COALESCE(mp_28, 0) + COALESCE(mp_29, 0) + COALESCE(mp_30, 0)
                     + COALESCE(mp_31, 0) + COALESCE(mp_32, 0) + COALESCE(mp_33, 0)
                     + COALESCE(mp_34, 0) + COALESCE(mp_35, 0) + COALESCE(mp_36, 0)
            END AS missed_pymt_cnt_last36m,
    
            greatest(0, valid_pymt_cnt_last3m  - missed_pymt_cnt_last3m )::int as made_pymt_cnt_last3m,
            greatest(0, valid_pymt_cnt_last6m  - missed_pymt_cnt_last6m )::int as made_pymt_cnt_last6m,
            greatest(0, valid_pymt_cnt_last9m  - missed_pymt_cnt_last9m )::int as made_pymt_cnt_last9m,
            greatest(0, valid_pymt_cnt_last12m - missed_pymt_cnt_last12m)::int as made_pymt_cnt_last12m,
            greatest(0, valid_pymt_cnt_last18m - missed_pymt_cnt_last18m)::int as made_pymt_cnt_last18m,
            greatest(0, valid_pymt_cnt_last24m - missed_pymt_cnt_last24m)::int as made_pymt_cnt_last24m,
            greatest(0, valid_pymt_cnt_last36m - missed_pymt_cnt_last36m)::int as made_pymt_cnt_last36m
    
    
     from PP_HS_BASE_BU_TL_8 ;
    """)

    duckdb.sql("""create table PP_HS_BASE_BU_TL_10 as
    select * ,
    least(36, (length(dpd_processed) / 3))::int as last_non_bl,
    CASE WHEN last_non_bl >= 1  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed,  1, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed,  1, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_1,
    
                CASE WHEN last_non_bl >= 2  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed,  4, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed,  4, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_2,
    
                CASE WHEN last_non_bl >= 3  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed,  7, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed,  7, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_3,
    
                CASE WHEN last_non_bl >= 4  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 10, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 10, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_4,
    
                CASE WHEN last_non_bl >= 5  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 13, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 13, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_5,
    
                CASE WHEN last_non_bl >= 6  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 16, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 16, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_6,
    
                CASE WHEN last_non_bl >= 7  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 19, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 19, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_7,
    
                CASE WHEN last_non_bl >= 8  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 22, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 22, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_8,
    
                CASE WHEN last_non_bl >= 9  THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 25, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 25, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_9,
    
                CASE WHEN last_non_bl >= 10 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 28, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 28, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_10,
    
                CASE WHEN last_non_bl >= 11 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 31, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 31, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_11,
    
                CASE WHEN last_non_bl >= 12 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 34, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 34, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_12,
    
                CASE WHEN last_non_bl >= 13 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 37, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 37, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_13,
    
                CASE WHEN last_non_bl >= 14 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 40, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 40, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_14,
    
                CASE WHEN last_non_bl >= 15 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 43, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 43, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_15,
    
                CASE WHEN last_non_bl >= 16 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 46, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 46, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_16,
    
                CASE WHEN last_non_bl >= 17 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 49, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 49, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_17,
    
                CASE WHEN last_non_bl >= 18 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 52, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 52, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_18,
    
                CASE WHEN last_non_bl >= 19 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 55, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 55, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_19,
    
                CASE WHEN last_non_bl >= 20 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 58, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 58, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_20,
    
                CASE WHEN last_non_bl >= 21 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 61, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 61, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_21,
    
                CASE WHEN last_non_bl >= 22 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 64, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 64, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_22,
    
                CASE WHEN last_non_bl >= 23 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 67, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 67, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_23,
    
                CASE WHEN last_non_bl >= 24 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 70, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 70, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_24,
    
                CASE WHEN last_non_bl >= 25 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 73, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 73, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_25,
    
                CASE WHEN last_non_bl >= 26 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 76, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 76, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_26,
    
                CASE WHEN last_non_bl >= 27 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 79, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 79, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_27,
    
                CASE WHEN last_non_bl >= 28 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 82, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 82, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_28,
    
                CASE WHEN last_non_bl >= 29 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 85, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 85, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_29,
    
                CASE WHEN last_non_bl >= 30 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 88, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 88, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_30,
    
                CASE WHEN last_non_bl >= 31 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 91, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 91, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_31,
    
                CASE WHEN last_non_bl >= 32 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 94, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 94, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_32,
    
                CASE WHEN last_non_bl >= 33 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 97, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 97, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_33,
    
                CASE WHEN last_non_bl >= 34 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 100, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 100, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_34,
    
                CASE WHEN last_non_bl >= 35 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 103, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 103, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_35,
    
                CASE WHEN last_non_bl >= 36 THEN
                  CASE WHEN regexp_matches(TRIM(SUBSTRING(dpd_processed, 106, 3)), '^[0-9]+$') > 0
                       THEN CAST(TRIM(SUBSTRING(dpd_processed, 106, 3)) AS INT)
                       ELSE NULL END
                ELSE NULL END AS payhist_36,
    
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '0 MONTH') - INTERVAL '1 DAY') AS dt1,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '1 MONTH') - INTERVAL '1 DAY') AS dt2,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '2 MONTH') - INTERVAL '1 DAY') AS dt3,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '3 MONTH') - INTERVAL '1 DAY') AS dt4,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '4 MONTH') - INTERVAL '1 DAY') AS dt5,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '5 MONTH') - INTERVAL '1 DAY') AS dt6,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '6 MONTH') - INTERVAL '1 DAY') AS dt7,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '7 MONTH') - INTERVAL '1 DAY') AS dt8,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '8 MONTH') - INTERVAL '1 DAY') AS dt9,
                (DATE_TRUNC('month',  rec_end_date - INTERVAL '9 MONTH') - INTERVAL '1 DAY') AS dt10,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '10 MONTH') - INTERVAL '1 DAY') AS dt11,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '11 MONTH') - INTERVAL '1 DAY') AS dt12,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '12 MONTH') - INTERVAL '1 DAY') AS dt13,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '13 MONTH') - INTERVAL '1 DAY') AS dt14,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '14 MONTH') - INTERVAL '1 DAY') AS dt15,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '15 MONTH') - INTERVAL '1 DAY') AS dt16,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '16 MONTH') - INTERVAL '1 DAY') AS dt17,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '17 MONTH') - INTERVAL '1 DAY') AS dt18,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '18 MONTH') - INTERVAL '1 DAY') AS dt19,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '19 MONTH') - INTERVAL '1 DAY') AS dt20,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '20 MONTH') - INTERVAL '1 DAY') AS dt21,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '21 MONTH') - INTERVAL '1 DAY') AS dt22,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '22 MONTH') - INTERVAL '1 DAY') AS dt23,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '23 MONTH') - INTERVAL '1 DAY') AS dt24,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '24 MONTH') - INTERVAL '1 DAY') AS dt25,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '25 MONTH') - INTERVAL '1 DAY') AS dt26,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '26 MONTH') - INTERVAL '1 DAY') AS dt27,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '27 MONTH') - INTERVAL '1 DAY') AS dt28,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '28 MONTH') - INTERVAL '1 DAY') AS dt29,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '29 MONTH') - INTERVAL '1 DAY') AS dt30,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '30 MONTH') - INTERVAL '1 DAY') AS dt31,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '31 MONTH') - INTERVAL '1 DAY') AS dt32,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '32 MONTH') - INTERVAL '1 DAY') AS dt33,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '33 MONTH') - INTERVAL '1 DAY') AS dt34,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '34 MONTH') - INTERVAL '1 DAY') AS dt35,
                (DATE_TRUNC('month', rec_end_date - INTERVAL '35 MONTH') - INTERVAL '1 DAY') AS dt36,
    
            CASE 
                WHEN coalesce(payhist_1,0)  > 0 THEN (DATE_DIFF('day', dt1, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_2,0)  > 0 THEN (DATE_DIFF('day', dt2 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_3,0)  > 0 THEN (DATE_DIFF('day', dt3 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_4,0)  > 0 THEN (DATE_DIFF('day', dt4 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_5,0)  > 0 THEN (DATE_DIFF('day', dt5 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_6,0)  > 0 THEN (DATE_DIFF('day', dt6 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_7,0)  > 0 THEN (DATE_DIFF('day', dt7 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_8,0)  > 0 THEN (DATE_DIFF('day', dt8 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_9,0)  > 0 THEN (DATE_DIFF('day', dt9 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_10,0) > 0 THEN (DATE_DIFF('day', dt10, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_11,0) > 0 THEN (DATE_DIFF('day', dt11, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_12,0) > 0 THEN (DATE_DIFF('day', dt12, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_13,0) > 0 THEN (DATE_DIFF('day', dt13, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_14,0) > 0 THEN (DATE_DIFF('day', dt14, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_15,0) > 0 THEN (DATE_DIFF('day', dt15, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_16,0) > 0 THEN (DATE_DIFF('day', dt16, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_17,0) > 0 THEN (DATE_DIFF('day', dt17, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_18,0) > 0 THEN (DATE_DIFF('day', dt18, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_19,0) > 0 THEN (DATE_DIFF('day', dt19, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_20,0) > 0 THEN (DATE_DIFF('day', dt20, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_21,0) > 0 THEN (DATE_DIFF('day', dt21, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_22,0) > 0 THEN (DATE_DIFF('day', dt22, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_23,0) > 0 THEN (DATE_DIFF('day', dt23, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_24,0) > 0 THEN (DATE_DIFF('day', dt24, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_25,0) > 0 THEN (DATE_DIFF('day', dt25, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_26,0) > 0 THEN (DATE_DIFF('day', dt26, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_27,0) > 0 THEN (DATE_DIFF('day', dt27, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_28,0) > 0 THEN (DATE_DIFF('day', dt28, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_29,0) > 0 THEN (DATE_DIFF('day', dt29, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_30,0) > 0 THEN (DATE_DIFF('day', dt30, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_31,0) > 0 THEN (DATE_DIFF('day', dt31, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_32,0) > 0 THEN (DATE_DIFF('day', dt32, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_33,0) > 0 THEN (DATE_DIFF('day', dt33, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_34,0) > 0 THEN (DATE_DIFF('day', dt34, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_35,0) > 0 THEN (DATE_DIFF('day', dt35, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_36,0) > 0 THEN (DATE_DIFF('day', dt36, scrub_date) - 1)::DECIMAL / 30.5
                ELSE NULL
            END AS time_since_last_0p,
    
            CASE
                WHEN coalesce(payhist_1,0)  >= 30 THEN (DATE_DIFF('day', dt1 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_2,0)  >= 30 THEN (DATE_DIFF('day', dt2 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_3,0)  >= 30 THEN (DATE_DIFF('day', dt3 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_4,0)  >= 30 THEN (DATE_DIFF('day', dt4 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_5,0)  >= 30 THEN (DATE_DIFF('day', dt5 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_6,0)  >= 30 THEN (DATE_DIFF('day', dt6 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_7,0)  >= 30 THEN (DATE_DIFF('day', dt7 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_8,0)  >= 30 THEN (DATE_DIFF('day', dt8 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_9,0)  >= 30 THEN (DATE_DIFF('day', dt9 , scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_10,0) >= 30 THEN (DATE_DIFF('day', dt10, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_11,0) >= 30 THEN (DATE_DIFF('day', dt11, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_12,0) >= 30 THEN (DATE_DIFF('day', dt12, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_13,0) >= 30 THEN (DATE_DIFF('day', dt13, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_14,0) >= 30 THEN (DATE_DIFF('day', dt14, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_15,0) >= 30 THEN (DATE_DIFF('day', dt15, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_16,0) >= 30 THEN (DATE_DIFF('day', dt16, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_17,0) >= 30 THEN (DATE_DIFF('day', dt17, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_18,0) >= 30 THEN (DATE_DIFF('day', dt18, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_19,0) >= 30 THEN (DATE_DIFF('day', dt19, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_20,0) >= 30 THEN (DATE_DIFF('day', dt20, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_21,0) >= 30 THEN (DATE_DIFF('day', dt21, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_22,0) >= 30 THEN (DATE_DIFF('day', dt22, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_23,0) >= 30 THEN (DATE_DIFF('day', dt23, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_24,0) >= 30 THEN (DATE_DIFF('day', dt24, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_25,0) >= 30 THEN (DATE_DIFF('day', dt25, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_26,0) >= 30 THEN (DATE_DIFF('day', dt26, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_27,0) >= 30 THEN (DATE_DIFF('day', dt27, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_28,0) >= 30 THEN (DATE_DIFF('day', dt28, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_29,0) >= 30 THEN (DATE_DIFF('day', dt29, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_30,0) >= 30 THEN (DATE_DIFF('day', dt30, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_31,0) >= 30 THEN (DATE_DIFF('day', dt31, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_32,0) >= 30 THEN (DATE_DIFF('day', dt32, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_33,0) >= 30 THEN (DATE_DIFF('day', dt33, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_34,0) >= 30 THEN (DATE_DIFF('day', dt34, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_35,0) >= 30 THEN (DATE_DIFF('day', dt35, scrub_date) - 1)::DECIMAL / 30.5
                WHEN coalesce(payhist_36,0) >= 30 THEN (DATE_DIFF('day', dt36, scrub_date) - 1)::DECIMAL / 30.5
                ELSE NULL
            END AS time_since_last_30p
    
    from PP_HS_BASE_BU_TL_9;
    
    
    drop table if exists PP_HS_BASE_BU_TL_11;
    create table PP_HS_BASE_BU_TL_11 as
    select *,
    
    greatest(
            coalesce(t_1,0), coalesce(t_2,0), coalesce(t_3,0),
            coalesce(t_4,0), coalesce(t_5,0), coalesce(t_6,0)
        )::int as max_dpd_l6m_tr,
    
    greatest(
            coalesce(t_1,0), coalesce(t_2,0), coalesce(t_3,0),
            coalesce(t_4,0), coalesce(t_5,0), coalesce(t_6,0),
            coalesce(t_7,0), coalesce(t_8,0), coalesce(t_9,0)
        )::int as max_dpd_l9m_tr,
    
    greatest(
            coalesce(t_1,0), coalesce(t_2,0), coalesce(t_3,0),
            coalesce(t_4,0), coalesce(t_5,0), coalesce(t_6,0),
            coalesce(t_7,0), coalesce(t_8,0), coalesce(t_9,0),
            coalesce(t_10,0), coalesce(t_11,0), coalesce(t_12,0)
        )::int as max_dpd_l12m_tr,
    
    GREATEST(
                COALESCE(payhist_1,0),  COALESCE(payhist_2,0),
                COALESCE(payhist_3,0),  COALESCE(payhist_4,0),
                COALESCE(payhist_5,0),  COALESCE(payhist_6,0),
                COALESCE(payhist_7,0),  COALESCE(payhist_8,0),
                COALESCE(payhist_9,0),  COALESCE(payhist_10,0),
                COALESCE(payhist_11,0), COALESCE(payhist_12,0),
                COALESCE(payhist_13,0), COALESCE(payhist_14,0),
                COALESCE(payhist_15,0), COALESCE(payhist_16,0),
                COALESCE(payhist_17,0), COALESCE(payhist_18,0),
                COALESCE(payhist_19,0), COALESCE(payhist_20,0),
                COALESCE(payhist_21,0), COALESCE(payhist_22,0),
                COALESCE(payhist_23,0), COALESCE(payhist_24,0),
                COALESCE(payhist_25,0), COALESCE(payhist_26,0),
                COALESCE(payhist_27,0), COALESCE(payhist_28,0),
                COALESCE(payhist_29,0), COALESCE(payhist_30,0),
                COALESCE(payhist_31,0), COALESCE(payhist_32,0),
                COALESCE(payhist_33,0), COALESCE(payhist_34,0),
                COALESCE(payhist_35,0), COALESCE(payhist_36,0)
            ) AS max_dpd
     from PP_HS_BASE_BU_TL_10;
    
    drop table if exists PP_HS_BASE_BU_TL_12;
    create table PP_HS_BASE_BU_TL_12 as
    select crn,reference_date,report_month,
    
    MIN(CASE WHEN f_pl = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCLASTTROP_PL_ONC,
    MIN(CASE WHEN f_uns = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCLASTTROP_UNS_ONC,
    
    SUM(case when f_pl =1 and  f_onc = 1 and (date_opened >= (scrub_date -INTERVAL '6 month')) then 1 else null end)  AS NO_TR_OPEN_L6M_PL_ONC,
     SUM(f_all * f_onc)         AS NO_TRADES_ALL_ONC,
    
    
    max(case when coalesce(f_cc,0)=1 then max_dpd_l6m_tr end) as max_dpd_l6m_cc_onc,
    max(case when coalesce(f_pl,0)=1  then max_dpd_l6m_tr  end) as max_dpd_l6m_pl_onc,
    max(case when coalesce(f_cc,0)=1 then max_dpd_l9m_tr end) as max_dpd_l9m_cc_onc,
    min(case when coalesce(f_uns,0)=1 and coalesce(open_flag,0)=1 then time_since_last_0p end) as mon_sin_last_0p_uns_op,
    min(case when coalesce(f_pl,0)=1 then time_since_last_0p end) as monsinlast_0p_pl_onc,
    
    case when sum(coalesce(valid_pymt_cnt_last24m,0))=0
             then null
             else 100.0 * sum(coalesce(cnt_0p_last24m,0)) / nullif(sum(coalesce(valid_pymt_cnt_last24m,0)),0)
        end as pct_0p_l24m_all_onc,
    
    case when sum(case when coalesce(f_pl,0)=1 then coalesce(valid_pymt_cnt_last24m,0) else 0 end)=0
             then null
             else 100.0 * sum(case when coalesce(f_pl,0)=1 then coalesce(cnt_0p_last24m,0) else 0 end)
                        / nullif(sum(case when coalesce(f_pl,0)=1 then coalesce(valid_pymt_cnt_last24m,0) else 0 end),0)
        end as pct_0p_l24m_pl_onc,
    
    case when sum(coalesce(valid_pymt_cnt_last18m,0))=0 then null
             else 100.0*sum(coalesce(missed_pymt_cnt_last18m,0))/nullif(sum(coalesce(valid_pymt_cnt_last18m,0)),0)
        end as pct_missed_pymt_last18m_all,
    
    ROUND(
                100.0 * SUM(
                    CASE
                        WHEN ACCOUNT_TYPE_CD IS NOT NULL
                         AND (open_flag = 1 OR date_closed >= ( scrub_date -INTERVAL '12 month'))
                         AND max_dpd_l12m_tr > 0
                        THEN 1 ELSE NULL
                    END
                )
                / NULLIF(
                    SUM(
                        CASE
                            WHEN ACCOUNT_TYPE_CD IS NOT NULL
                             AND (open_flag = 1 OR date_closed >= ( scrub_date -INTERVAL '12 month'))
                            THEN 1 ELSE NULL
                        END
                    ), 0
                )
            ,4) AS pct_tr_0p_l12m_all_onc,
    
    SUM(CASE
                WHEN ACCOUNT_TYPE_CD IN (05,69)
                 AND open_flag = 0 THEN 1 ELSE 0 END
            ) AS cnt_closed_pl,
    
    SUM(CASE
                WHEN ACCOUNT_TYPE_CD IN (05,69)
                 AND open_flag = 0
                 AND max_dpd < 1 THEN 1 ELSE 0 END
            ) AS cnt_good_closed_pl,
    
    SUM(CASE WHEN (account_type_cd IN (5,69) AND open_flag = 1)
                THEN sanction_amount ELSE 0 END) AS sum_sanc_amt_pl_lv,
    SUM(CASE WHEN account_type_cd in (10, 16, 31, 35, 36) AND open_flag = 1
                THEN sanction_amount ELSE 0 END) AS sum_sanc_amt_cc_lv,     
    
     MAX(CASE WHEN f_cc = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_CC_LV,
    
            MIN(CASE WHEN f_allsal1l = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCLASTTROP_ALLSAL1L_ONC,
    
            MAX(CASE WHEN f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_ALL_LV,
    
            MAX(CASE WHEN f_allsag20k = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_ALL_SAG20K_LV,
    
            -- MAX(CASE WHEN f_allsag1l = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_ALLSAG1L_ONC,
    
            MIN(CASE WHEN f_hra = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCLASTTROP_HRA_ONC,
    
            MAX(CASE WHEN f_exccgled = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_EXCCGLED_LV,
    
            MIN(CASE WHEN f_pl = 1 and f_allsag20k=1 and  f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCLASTTROP_PL_SAG20K_ONC,
    
    
            MAX(CASE WHEN f_allsag1l = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_ALLSAG1L_LV,
            MAX(CASE WHEN f_allsal1l = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_ALLSAL1L_LV,
    
            
    
    
            MAX(CASE WHEN f_cc = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_CC_ONC,
            MAX(CASE WHEN f_onc=1 then time_since_tr_open  ELSE NULL END) AS MONSNCFIRSTTROP_ALL_ONC,
            MAX(CASE WHEN f_exc_cc = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS TIMESNCFIRSTTROP_EXC_CC_ONC,
    
    
            MIN(CASE WHEN f_exccgled = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS monsnclasttrop_exccgled_lv,
    
            MIN(CASE WHEN f_cc = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS monsnclasttrop_cc_onc,
    
    
            MIN(CASE WHEN f_allsal1l = 1 and f_lv =1 then time_since_tr_open  ELSE NULL END) AS MONSNCLASTTROP_ALLSAL1L_LV,
    
    
            MIN(CASE WHEN f_exccgled = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCLASTTROP_EXCCGLED_ONC,
            -- MIN(CASE WHEN f_uns = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS MONSNCLASTTROP_UNS_ONC,
    
            MIN(CASE WHEN f_pl = 1 and f_allsal20k = 1 and f_onc =1 then time_since_tr_open  ELSE NULL END) AS monsnclasttrop_pl_sal20k_onc,
            MIN(CASE WHEN f_pl = 1 and f_allsag20k = 1 and f_onc =1 then time_since_tr_close ELSE NULL END) AS monsnclasttrcl_pl_sag20k_onc,
               -- -------- CONSUMER DURABLE --------
            MAX(CASE WHEN f_cd = 1 AND f_onc = 1 THEN time_since_tr_open ELSE NULL END) AS MONSNCFIRSTTROP_CD_ONC,
            MIN(CASE WHEN f_cd = 1 AND f_onc = 1 THEN time_since_tr_open ELSE NULL END) AS MONSNCLASTTROP_CD_ONC,
            SUM(CASE WHEN f_cd = 1 AND f_onc = 1 THEN 1 ELSE 0 END) AS NO_TRADES_CD_ONC,
    
            -- -------- ALL_SAG20K --------
            MAX(CASE WHEN f_allsag20k = 1 AND f_onc = 1 THEN time_since_tr_open ELSE NULL END) AS MONSNCFIRSTTROP_ALL_SAG20K_ONC,
            MIN(CASE WHEN f_allsag20k = 1 AND f_onc = 1 THEN time_since_tr_open ELSE NULL END) AS MONSNCLASTTROP_ALL_SAG20K_ONC,
            SUM(CASE WHEN f_allsag20k = 1 AND f_onc = 1 THEN 1 ELSE 0 END) AS NO_TRADES_ALL_SAG20K_ONC,
    
            -- -------- ALL_SAG1L --------
            MAX(CASE WHEN f_allsag1l = 1 AND f_onc = 1 THEN time_since_tr_open ELSE NULL END) AS MONSNCFIRSTTROP_allSAG1L_ONC,
            MIN(CASE WHEN f_allsag1l = 1 AND f_onc = 1 THEN time_since_tr_open ELSE NULL END) AS MONSNCLASTTROP_allSAG1L_ONC,
            SUM(CASE WHEN f_allsag1l = 1 AND f_onc = 1 THEN 1 ELSE 0 END) AS NO_TRADES_allSAG1L_ONC,
    
          
               -- UNS:
               MAX(CASE WHEN f_uns = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCFIRSTTROP_UNS_ONC,
            --    MIN(CASE WHEN f_uns = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCLASTTROP_UNS_ONC,
               SUM(CASE WHEN f_uns = 1 AND f_onc = 1 THEN 1 ELSE 0 END) AS NO_TRADES_UNS_ONC,
    
               -- BL:
              MAX(CASE WHEN f_bl = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCFIRSTTROP_BL_ONC,
                MIN(CASE WHEN f_bl = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCLASTTROP_BL_ONC,
               SUM(CASE WHEN f_bl = 1 AND f_onc = 1 THEN 1 ELSE 0 END) AS NO_TRADES_BL_ONC,
    
               -- PL:
                MAX(CASE WHEN f_pl = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCFIRSTTROP_PL_ONC,
                -- MIN(CASE WHEN f_pl = 1 AND f_onc = 1 THEN time_since_tr_open END) AS MONSNCLASTTROP_PL_ONC,
                SUM(CASE WHEN f_pl = 1 AND f_onc = 1 THEN 1 ELSE 0 END) AS NO_TRADES_PL_ONC,
    
    
                MAX(CASE WHEN f_plbl = 1 AND f_onc = 1 AND date_opened >= (scrub_date -INTERVAL '12 month') THEN time_since_tr_open END) AS MONSNCFIRSTTROP_PLBL_ONC_L12M,
                MIN(CASE WHEN f_plbl = 1 AND f_onc = 1 AND date_opened >= (scrub_date -INTERVAL '12 month') THEN time_since_tr_open END) AS MONSNCLASTTROP_PLBL_ONC_L12M,
                SUM(CASE WHEN f_plbl = 1 AND f_onc = 1 AND date_opened >= (scrub_date -INTERVAL '12 month') THEN 1 ELSE 0 END) AS NO_TRADES_PLBL_ONC_L12M,
    
    
            -- ---------------- PLBL — last 6 months ----------------
            MAX(CASE WHEN f_plbl = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '6 month')
                     THEN time_since_tr_open END) AS MONSNCFIRSTTROP_PLBL_ONC_L6M,
            MIN(CASE WHEN f_plbl = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '6 month')
                     THEN time_since_tr_open END) AS MONSNCLASTTROP_PLBL_ONC_L6M,
            SUM(CASE WHEN f_plbl = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '6 month')
                     THEN 1 ELSE 0 END) AS NO_TRADES_PLBL_ONC_L6M,
    
            -- ---------------- HL_LAP — last 9 months ----------------
            MAX(CASE WHEN f_hllap = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '9 month')
                     THEN time_since_tr_open END) AS MONSNCFIRSTTROP_HL_LAP_ONC_L9M,
            MIN(CASE WHEN f_hllap = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '9 month')
                     THEN time_since_tr_open END) AS MONSNCLASTTROP_HL_LAP_ONC_L9M,
            SUM(CASE WHEN f_hllap = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '9 month')
                     THEN 1 ELSE 0 END) AS NO_TRADES_HL_LAP_ONC_L9M,
    
            -- ---------------- TWL — last 24 months ----------------
            MAX(CASE WHEN f_twl = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN time_since_tr_open END) AS MONSNCFIRSTTROP_TWL_ONC_L24M,
            MIN(CASE WHEN f_twl = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN time_since_tr_open END) AS MONSNCLASTTROP_TWL_ONC_L24M,
            SUM(CASE WHEN f_twl = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN 1 ELSE 0 END) AS NO_TRADES_TWL_ONC_L24M,
    
            -- ---------------- HL_LAP — last 24 months ----------------
            MAX(CASE WHEN f_hllap = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN time_since_tr_open END) AS MONSNCFIRSTTROP_HL_LAP_ONC_L24M,
            MIN(CASE WHEN f_hllap = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN time_since_tr_open END) AS MONSNCLASTTROP_HL_LAP_ONC_L24M,
            SUM(CASE WHEN f_hllap = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN 1 ELSE 0 END) AS NO_TRADES_HL_LAP_ONC_L24M,
    
            -- ---------------- ALL — last 24 months ----------------
            MAX(CASE WHEN f_all = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN time_since_tr_open END) AS MONSNCFIRSTTROP_ALL_ONC_L24M,
            MIN(CASE WHEN f_all = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN time_since_tr_open END) AS MONSNCLASTTROP_ALL_ONC_L24M,
            SUM(CASE WHEN f_all = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '24 month')
                     THEN 1 ELSE 0 END) AS NO_TRADES_ALL_ONC_L24M,
    
            -- ---------------- CL — last 12 months ----------------
            MAX(CASE WHEN f_cd = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '12 month')
                     THEN time_since_tr_open END) AS MONSNCFIRSTTROP_CL_ONC_L12M,
            MIN(CASE WHEN f_cd = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '12 month')
                     THEN time_since_tr_open END) AS MONSNCLASTTROP_CL_ONC_L12M,
            SUM(CASE WHEN f_cd = 1 AND f_onc = 1 AND date_opened >= ( scrub_date -INTERVAL '12 month')
                     THEN 1 ELSE 0 END) AS NO_TRADES_CL_ONC_L12M,
    
            SUM(CASE WHEN (account_type_cd in (10, 16, 31, 35, 36) AND open_flag = 1)
                THEN out_standing_balance ELSE 0 END) AS sum_currbal_cc_lv,
            SUM(CASE WHEN (account_type_cd IN (5,69) AND open_flag = 1)
                THEN out_standing_balance ELSE 0 END) AS sum_currbal_pl_lv,
    
    sum(case when f_uns = 1 and f_onc = 1 and (date_opened >= (scrub_date -INTERVAL '24 month')) then 1 else null end) as no_tr_open_l24m_uns_onc
    
    from PP_HS_BASE_BU_TL_11
    group by crn,reference_date,report_month;
    
    drop table if exists PP_HS_BASE_BU_TL_13;
    create table PP_HS_BASE_BU_TL_13 as
    select *,
    CASE WHEN sum_sanc_amt_cc_lv = 0 THEN NULL
             ELSE ROUND((sum_currbal_cc_lv / sum_sanc_amt_cc_lv) * 100, 4) END AS pct_bal_cc_lv,
    
    CASE WHEN sum_sanc_amt_pl_lv = 0 THEN NULL
             ELSE ROUND((sum_currbal_pl_lv / sum_sanc_amt_pl_lv) * 100, 4) END AS pct_bal_pl_lv,
    
    CASE 
            WHEN (MONSNCFIRSTTROP_CL_ONC_L12M <= 0 OR MONSNCFIRSTTROP_CL_ONC_L12M IS NULL)
              OR (MONSNCLASTTROP_CL_ONC_L12M <= 0 OR MONSNCLASTTROP_CL_ONC_L12M IS NULL)
              OR (NO_TRADES_CL_ONC_L12M <= 0 OR NO_TRADES_CL_ONC_L12M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_CL_ONC_L12M - MONSNCLASTTROP_CL_ONC_L12M) / NO_TRADES_CL_ONC_L12M
        END AS interpurchase_time_l12m_CL,
    
    CASE 
            WHEN (MONSNCFIRSTTROP_PLBL_ONC_L12M <= 0 OR MONSNCFIRSTTROP_PLBL_ONC_L12M IS NULL)
              OR (MONSNCLASTTROP_PLBL_ONC_L12M <= 0 OR MONSNCLASTTROP_PLBL_ONC_L12M IS NULL)
              OR (NO_TRADES_PLBL_ONC_L12M <= 0 OR NO_TRADES_PLBL_ONC_L12M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_PLBL_ONC_L12M - MONSNCLASTTROP_PLBL_ONC_L12M) / NO_TRADES_PLBL_ONC_L12M
          END AS interpurchase_time_l12m_PLBL,
    
    CASE 
            WHEN (MONSNCFIRSTTROP_ALL_ONC_L24M <= 0 OR MONSNCFIRSTTROP_ALL_ONC_L24M IS NULL)
              OR (MONSNCLASTTROP_ALL_ONC_L24M <= 0 OR MONSNCLASTTROP_ALL_ONC_L24M IS NULL)
              OR (NO_TRADES_ALL_ONC_L24M <= 0 OR NO_TRADES_ALL_ONC_L24M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_ALL_ONC_L24M - MONSNCLASTTROP_ALL_ONC_L24M) / NO_TRADES_ALL_ONC_L24M
        END AS interpurchase_time_l24m_ALL,
    
    CASE 
            WHEN (MONSNCFIRSTTROP_HL_LAP_ONC_L24M <= 0 OR MONSNCFIRSTTROP_HL_LAP_ONC_L24M IS NULL)
              OR (MONSNCLASTTROP_HL_LAP_ONC_L24M <= 0 OR MONSNCLASTTROP_HL_LAP_ONC_L24M IS NULL)
              OR (NO_TRADES_HL_LAP_ONC_L24M <= 0 OR NO_TRADES_HL_LAP_ONC_L24M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_HL_LAP_ONC_L24M - MONSNCLASTTROP_HL_LAP_ONC_L24M) / NO_TRADES_HL_LAP_ONC_L24M
        END AS interpurchase_time_l24m_HL_LAP,
    
    CASE 
            WHEN (MONSNCFIRSTTROP_TWL_ONC_L24M <= 0 OR MONSNCFIRSTTROP_TWL_ONC_L24M IS NULL)
              OR (MONSNCLASTTROP_TWL_ONC_L24M <= 0 OR MONSNCLASTTROP_TWL_ONC_L24M IS NULL)
              OR (NO_TRADES_TWL_ONC_L24M <= 0 OR NO_TRADES_TWL_ONC_L24M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_TWL_ONC_L24M - MONSNCLASTTROP_TWL_ONC_L24M) / NO_TRADES_TWL_ONC_L24M
        END AS interpurchase_time_l24m_TWL,
    
    CASE 
            WHEN (MONSNCFIRSTTROP_PLBL_ONC_L6M <= 0 OR MONSNCFIRSTTROP_PLBL_ONC_L6M IS NULL)
              OR (MONSNCLASTTROP_PLBL_ONC_L6M <= 0 OR MONSNCLASTTROP_PLBL_ONC_L6M IS NULL)
              OR (NO_TRADES_PLBL_ONC_L6M <= 0 OR NO_TRADES_PLBL_ONC_L6M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_PLBL_ONC_L6M - MONSNCLASTTROP_PLBL_ONC_L6M) / NO_TRADES_PLBL_ONC_L6M
        END AS interpurchase_time_l6m_PLBL,
    CASE 
            WHEN (MONSNCFIRSTTROP_HL_LAP_ONC_L9M <= 0 OR MONSNCFIRSTTROP_HL_LAP_ONC_L9M IS NULL)
              OR (MONSNCLASTTROP_HL_LAP_ONC_L9M <= 0 OR MONSNCLASTTROP_HL_LAP_ONC_L9M IS NULL)
              OR (NO_TRADES_HL_LAP_ONC_L9M <= 0 OR NO_TRADES_HL_LAP_ONC_L9M IS NULL)
            THEN NULL
            ELSE (MONSNCFIRSTTROP_HL_LAP_ONC_L9M - MONSNCLASTTROP_HL_LAP_ONC_L9M) / NO_TRADES_HL_LAP_ONC_L9M
        END AS interpurchase_time_l9m_HL_LAP
    
    from PP_HS_BASE_BU_TL_12;
    """)

    duckdb.sql("""drop table if exists PP_HS_BASE_BU_MAXDPD_TL_1;
    CREATE TABLE PP_HS_BASE_BU_MAXDPD_TL_1 AS
    select 
            crn,
            reference_date,
            report_month as report_month,
            creditlimit,
            date_closed,
            date_opened,
            datereported_trades,
            dpd_string,
            pay_hist_end_date,
            pay_hist_start_date,
            sanction_amount,
            out_standing_balance,
            over_due_amount,
            emi,
            high_credit_amount,
            tu_score,
            last_payment_date,
            loan_type_new,
            loan_status,
            loan_classification,
            ownership_type,
            sector,
            base,
    payhist_1,payhist_2,payhist_3,payhist_4,payhist_5,payhist_6,payhist_7,payhist_8,payhist_9,payhist_10
    ,payhist_11,payhist_12,payhist_13,payhist_14,payhist_15,payhist_16,payhist_17,payhist_18,payhist_19,payhist_20
    ,payhist_21,payhist_22,payhist_23,payhist_24,payhist_25,payhist_26,payhist_27,payhist_28,payhist_29,payhist_30
    ,payhist_31,payhist_32,payhist_33,payhist_34,payhist_35,payhist_36,
    dt1,dt2,dt3,dt4,dt5,dt6,dt7,dt8,dt9,dt10
    ,dt11,dt12,dt13,dt14,dt15,dt16,dt17,dt18,dt19,dt20
    ,dt21,dt22,dt23,dt24,dt25,dt26,dt27,dt28,dt29,dt30
    ,dt31,dt32,dt33,dt34,dt35,dt36,
    greatest(
    payhist_1,payhist_2,payhist_3,payhist_4,payhist_5,payhist_6,payhist_7,payhist_8,payhist_9,payhist_10
    ,payhist_11,payhist_12,payhist_13,payhist_14,payhist_15,payhist_16,payhist_17,payhist_18,payhist_19,payhist_20
    ,payhist_21,payhist_22,payhist_23,payhist_24,payhist_25,payhist_26,payhist_27,payhist_28,payhist_29,payhist_30
    ,payhist_31,payhist_32,payhist_33,payhist_34,payhist_35,payhist_36) as MAX_DPD,
    
    case 
    when payhist_1 >= MAX_DPD THEN dt1
    WHEN payhist_2 >= MAX_DPD THEN dt2
    WHEN payhist_3 >= MAX_DPD THEN dt3
    WHEN payhist_4 >= MAX_DPD THEN dt4
    WHEN payhist_5 >= MAX_DPD THEN dt5
    WHEN payhist_6 >= MAX_DPD THEN dt6
    WHEN payhist_7 >= MAX_DPD THEN dt7
    WHEN payhist_8 >= MAX_DPD THEN dt8
    WHEN payhist_9 >= MAX_DPD THEN dt9
    WHEN payhist_10 >= MAX_DPD THEN dt10
    WHEN payhist_11 >= MAX_DPD THEN dt11
    WHEN payhist_12 >= MAX_DPD THEN dt12
    WHEN payhist_13 >= MAX_DPD THEN dt13
    WHEN payhist_14 >= MAX_DPD THEN dt14
    WHEN payhist_15 >= MAX_DPD THEN dt15
    WHEN payhist_16 >= MAX_DPD THEN dt16
    WHEN payhist_17 >= MAX_DPD THEN dt17
    WHEN payhist_18 >= MAX_DPD THEN dt18
    WHEN payhist_19 >= MAX_DPD THEN dt19
    WHEN payhist_20 >= MAX_DPD THEN dt20
    WHEN payhist_21 >= MAX_DPD THEN dt21
    WHEN payhist_22 >= MAX_DPD THEN dt22
    WHEN payhist_23 >= MAX_DPD THEN dt23
    WHEN payhist_24 >= MAX_DPD THEN dt24
    WHEN payhist_25 >= MAX_DPD THEN dt25
    WHEN payhist_26 >= MAX_DPD THEN dt26
    WHEN payhist_27 >= MAX_DPD THEN dt27
    WHEN payhist_28 >= MAX_DPD THEN dt28
    WHEN payhist_29 >= MAX_DPD THEN dt29
    WHEN payhist_30 >= MAX_DPD THEN dt30
    WHEN payhist_31 >= MAX_DPD THEN dt31
    WHEN payhist_32 >= MAX_DPD THEN dt32
    WHEN payhist_33 >= MAX_DPD THEN dt33
    WHEN payhist_34 >= MAX_DPD THEN dt34
    WHEN payhist_35 >= MAX_DPD THEN dt35
    WHEN payhist_36 >= MAX_DPD THEN dt36
    end AS MAX_DPD_DATE,
    
    date_diff('month',MAX_DPD_DATE,SCRUB_DATE) AS MONTHS_SINCE_MAX_DPD
    
    from PP_HS_BASE_BU_TL_10;
    
    drop table if exists PP_HS_BASE_BU_MAXDPD_TL_2;
    CREATE TABLE PP_HS_BASE_BU_MAXDPD_TL_2 AS
    select * from 
    (SELECT *,
    ROW_NUMBER() OVER(PARTITION BY CRN,REFERENCE_DATE ORDER BY max_dpd desc, months_since_max_dpd asc) as rnk 
    FROM PP_HS_BASE_BU_MAXDPD_TL_1
    ) where rnk=1;""")

    PP_HS_BU_ENQ_tl_1 = duckdb.sql(f"""SELECT * FROM read_csv_auto('{enq_input_file}') """).df()
    
    duckdb.sql("""drop table if exists PP_HS_BU_ENQ_tl_2;
    CREATE TABLE PP_HS_BU_ENQ_tl_2 AS
    SELECT *,
        -- Scrub date: last day of previous month
        
        LAST_DAY(strptime(report_month || '01', '%Y%m%d') - INTERVAL '1 MONTH') AS scrub_date,
     
        -- Onus Flag
        CASE
            WHEN EnquiringMemberShortName = 'KOTAK BANK' THEN 1
            ELSE 0
        END AS ONUS,
-- Account Type CD
        CASE
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('AUTO LOAN (PERSONAL)', 'AUTO LOAN') THEN 1
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'HOUSING LOAN' THEN 2
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'PROPERTY LOAN' THEN 3
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('LOAN AGAINST SHARES/SECURITIES', 'LOAN AGAINST SHARES / SECURITIES') THEN 4
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'PERSONAL LOAN' THEN 5
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'CONSUMER LOAN' THEN 6
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'GOLD LOAN' THEN 7
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'EDUCATION LOAN' THEN 8
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'LOAN TO PROFESSIONAL' THEN 9
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'CREDIT CARD' THEN 10
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'LEASING' THEN 11
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'OVERDRAFT' THEN 12
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'TWO-WHEELER LOAN' THEN 13
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'NON-FUNDED CREDIT FACILITY' THEN 14
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'LOAN AGAINST BANK DEPOSITS' THEN 15
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'FLEET CARD' THEN 16
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'COMMERCIAL VEHICLE LOAN' THEN 17
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'TELCO - WIRELESS' THEN 18
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'TELCO - BROADBAND' THEN 19
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'TELCO - LANDLINE' THEN 20
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'SELLER FINANCING' THEN 21
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'SELLER FINANCING SOFT (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 22
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'GECL LOAN SECURED' THEN 23
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'GECL LOAN UNSECURED' THEN 24
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'SECURED CREDIT CARD' THEN 31
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'USED CAR LOAN' THEN 32
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'CONSTRUCTION EQUIPMENT LOAN' THEN 33
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'TRACTOR LOAN' THEN 34
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'CORPORATE CREDIT CARD' THEN 35
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'KISAN CREDIT CARD' THEN 36
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'LOAN ON CREDIT CARD' THEN 37
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'PRIME MINISTER JAAN DHAN YOJANA - OVERDRAFT' THEN 38
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'MUDRA LOANS - SHISHU / KISHOR / TARUN' THEN 39
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'MICROFINANCE - BUSINESS LOAN' THEN 40
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'MICROFINANCE - PERSONAL LOAN' THEN 41
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'MICROFINANCE - HOUSING LOAN' THEN 42
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('MICROFINANCE - OTHER', 'MICROFINANCE - OTHERS') THEN 43
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'PRADHAN MANTRI AWAS YOJANA - CREDIT LINK SUBSIDY SCHEME MAY CLSS' THEN 44
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'P2P PERSONAL LOAN' THEN 45
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'P2P AUTO LOAN' THEN 46
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'P2P EDUCATION LOAN' THEN 47
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'BUSINESS LOAN - SECURED' THEN 50
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'BUSINESS LOAN - GENERAL' THEN 51
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('BUSINESS LOAN - PRIORITY SECTOR - SMALL BUSINESS', 'BLPSSB BUSINESS LOAN -PRIORITY SECTOR - SMALL BUSINESS') THEN 52
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('BUSINESS LOAN - PRIORITY SECTOR - AGRICULTURE', 'BLPSAGR BUSINESS LOAN - PRIORITY SECTOR - AGRICULTURE') THEN 53
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('BUSINESS LOAN - PRIORITY SECTOR - OTHERS', 'BLPSOTH BUSINESS LOAN - PRIORITY SECTOR - OTHERS') THEN 54
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('BUSINESS NON-FUNDED CREDIT FACILITY - GENERAL', 'BNFCFGEN BUSINESS NONFUNDED CREDIT FACILITY - GENERAL') THEN 55
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN (
            'BUSINESS NON-FUNDED CREDIT FACILITY - PRIORITY SECTOR - SMALL BUSINESS',
            'BNFCFPSSB BUSINESS NONFUNDED CREDIT FACILITY - PRIORITY SECTOR - SMALL BUSINESS',
            'BUSINESS NON-FUNDED CREDIT FACILITY-PRIORITY SECTOR- SMALL BUSINESS'
        ) THEN 56
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN (
            'BUSINESS NON-FUNDED CREDIT FACILITY - PRIORITY SECTOR - AGRICULTURE',
            'BNFCFPSAGR BUSINESS NONFUNDED CREDIT FACILITY - PRIORITY SECTOR ?AGRICULTURE',
            'BUSINESS NON-FUNDED CREDIT FACILITY-PRIORITY SECTOR-AGRICULTURE'
        ) THEN 57
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN (
            'BUSINESS NON-FUNDED CREDIT FACILITY - PRIORITY SECTOR-OTHERS',
            'BNFCFPSOTH BUSINESS NONFUNDED CREDIT FACILITY - PRIORITY SECTOROTHERS',
            'BUSINESS NON-FUNDED CREDIT FACILITY-PRIORITY SECTOR-OTHERS'
        ) THEN 58
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('BUSINESS LOAN AGAINST BANK DEPOSITS', 'BLABD BUSINESS LOAN AGAINST BANK DEPOSITS') THEN 59
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'BUSINESS LOAN - UNSECURED' THEN 61
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'MICROFINANCE DETAILED REPORT (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 80
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'SUMMARY REPORT (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 81
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'LOCATE PLUS FOR INSURANCE (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 88
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'ACCOUNT REVIEW (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 90
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'RETRO ENQUIRY (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 91
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'LOCATE PLUS (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 92
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'ADVISER LIABILITY (APPLICABLE TO ENQUIRY PURPOSE ONLY)' THEN 97
        WHEN UPPER(ENQUIRYPURPOSE_NEW) IN ('OTHER', '') THEN 0
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'SECURED (ACCOUNT GROUP FOR PORTFOLIO REVIEW RESPONSE)' THEN 98
        WHEN UPPER(ENQUIRYPURPOSE_NEW) = 'UNSECURED (ACCOUNT GROUP FOR PORTFOLIO REVIEW RESPONSE)' THEN 99
        ELSE NULL
    END AS ACCOUNT_TYPE_CD
     
    FROM PP_HS_BU_ENQ_tl_1;
     
    drop table if exists PP_HS_BU_ENQ_tl_3;
    CREATE TABLE PP_HS_BU_ENQ_tl_3 AS
    SELECT *
        -- Secured/Unsecured Flag
        ,CASE
            WHEN ACCOUNT_TYPE_CD IN (5, 6, 8, 9, 12, 13, 24, 37, 38, 39, 40, 41, 43, 45, 47, 51, 52, 53, 54, 55, 56, 57, 58, 61, 0) THEN 'UNSEC'
            WHEN ACCOUNT_TYPE_CD IN (1, 2, 3, 4, 7, 11, 14, 15, 17, 23, 32, 33, 34, 42, 44, 46, 50, 59) THEN 'SEC'
            ELSE 'OTHERS'
        END AS SEC_UNSEC_FLAG
     
        -- Difference in days and months
        ,date_diff('day', DATEOFENQUIRY, scrub_date) AS diff
     
        ,ROUND(date_diff('day', DATEOFENQUIRY, scrub_date) / 30.5,4) AS diff_month
    
     
    FROM PP_HS_BU_ENQ_tl_2;
     
     
    drop table if exists PP_HS_BU_ENQ_tl_4;
    create table PP_HS_BU_ENQ_tl_4 as
    select crn,reference_date
    ,sum(case when SEC_UNSEC_FLAG = 'UNSEC' THEN 1 ELSE 0 END) AS enq_unsec_all
    ,sum(case when SEC_UNSEC_FLAG = 'UNSEC' AND diff_month <= 3 THEN 1 ELSE 0 END) AS enq_unsec_03M
    ,sum(case when SEC_UNSEC_FLAG = 'UNSEC' AND diff_month <= 6 THEN 1 ELSE 0 END) AS enq_unsec_06M
    ,sum(case when SEC_UNSEC_FLAG = 'UNSEC' AND diff_month <= 12 THEN 1 ELSE 0 END) AS enq_unsec_12M
    ,sum(case when SEC_UNSEC_FLAG = 'UNSEC' AND diff_month <= 24 THEN 1 ELSE 0 END) AS enq_unsec_24M
     
    from PP_HS_BU_ENQ_tl_3
    where DateOfEnquiry <= scrub_date
    group by crn,reference_date;
    
    drop table if exists PP_HS_BASE_BU_TL_14;
    create table PP_HS_BASE_BU_TL_14 as
    select a.*,b.enq_unsec_12M
    
    ,case
            when coalesce(b.enq_unsec_24M, 0) <= 0
                 and coalesce(a.no_tr_open_l24m_uns_onc, 0) <= 0 then null
            when coalesce(b.enq_unsec_24M, 0) <= 0 then null
            else round(
                    (coalesce(a.no_tr_open_l24m_uns_onc, 0)::decimal(18,6)
                     / nullif(b.enq_unsec_24M, 0)::decimal(18,6)),
                    4
                 ) * 100
        end as tr_to_enq_ratio_uns_l24m
    from PP_HS_BASE_BU_TL_13 a
    left join PP_HS_BU_ENQ_tl_4 b
    on a.crn = b.crn AND A.REFERENCE_DATE = B.REFERENCE_DATE;
    """)

    duckdb.sql("""create table BU_Feats as
    SELECT A.*, MAX_DPD, MAX_DPD_DATE, months_since_max_dpd 
    FROM PP_HS_BASE_BU_TL_14 A
    LEFT JOIN PP_HS_BASE_BU_MAXDPD_TL_2 B
    ON A.CRN = B.CRN""")
    
    df_feats = duckdb.sql("SELECT * FROM BU_Feats").df()
    df_feats.to_csv(bu_feats_output, index=False)
    
    # Export the per-tradeline table that already carries payhist_1..36 / dt1..36 /
    # MAX_DPD / MAX_DPD_DATE / MONTHS_SINCE_MAX_DPD (a later checkpoint of the SAME
    # per-tradeline chain as _TL_9), so BU_TL contains every dpd_data column.
    df_feats = duckdb.sql("SELECT * FROM PP_HS_BASE_BU_MAXDPD_TL_1").df()
    df_feats.to_csv(bu_tl_output, index=False)
    
    print("Completed")
    

if __name__ == "__main__":
    main()