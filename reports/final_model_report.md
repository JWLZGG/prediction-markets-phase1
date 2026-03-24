# Final Model Report

## 1. Objective

Build a reproducible prediction-market research and monitoring pipeline that benchmarks model skill against naive and market baselines, then applies the learned model to current markets.

## 2. Dataset and framing

- Historical resolved-market pipeline built on recent Polymarket data.
- Snapshot framing evaluated at open, midpoint, and 24h-before-close.
- Current-market monitoring built for Polymarket and exploratory Kalshi scoring.

## 3. Key conclusions

- The 24h-before-close snapshot is the strongest offline setting.
- Midpoint retains some signal, but is weaker than 24h.
- Open is not currently robust in the evaluation frame.
- Polymarket current scoring is cleaner because it is closer to the model’s training domain.
- Kalshi current scoring works as an exploratory cross-venue monitor, but remains noisier and should be interpreted cautiously.

## 4. Offline snapshot summary

# Offline Snapshot Summary

This compares naive, market, and model Brier scores across open, mid, and 24h snapshots.



Open is reported using the practical v1 definition: first available observed price within 24 hours of market creation.

A strict 60-minute open definition is retained as a diagnostic only, and current history data supports very few such rows.



| snapshot | rows_used | strict_open_rows_60m | avg_minutes_from_open_to_snapshot | naive_brier | market_brier | model_brier | bss_vs_naive | bss_vs_market | takeaway |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| open | 248 | 1.000000 | 438.367350 | 0.250000 | 0.141263 | 0.112399 | 0.550406 | 0.204333 | model beats market |
| mid | 431 |  |  | 0.250000 | 0.073034 | 0.066788 | 0.732848 | 0.085518 | model beats market |
| 24h | 434 |  |  | 0.250000 | 0.046290 | 0.036890 | 0.852438 | 0.203064 | model beats market |



## 5. Best 24h feature directionality / coefficients

# Best 24h Coefficients

## Top positive coefficients

| feature | coefficient |
| --- | --- |
| num__market_implied_prob | 3.143656 |
| cat__category_fallback_Sports | 0.560604 |
| num__log_volume | 0.370494 |
| num__duration_hours | 0.350855 |
| cat__category_fallback_Politics | 0.248039 |
| cat__category_fallback_Other | 0.215858 |
| num__distance_from_0_5 | 0.157901 |
| cat__category_fallback_Business/Tech | -0.036083 |
| cat__category_fallback_Culture/Entertainment | -0.040934 |
| num__prob_change_24h | -0.177562 |
| num__history_points_count | -0.408132 |
| cat__category_fallback_Crypto | -0.957730 |

## Top negative coefficients

| feature | coefficient |
| --- | --- |
| cat__category_fallback_Crypto | -0.957730 |
| num__history_points_count | -0.408132 |
| num__prob_change_24h | -0.177562 |
| cat__category_fallback_Culture/Entertainment | -0.040934 |
| cat__category_fallback_Business/Tech | -0.036083 |
| num__distance_from_0_5 | 0.157901 |
| cat__category_fallback_Other | 0.215858 |
| cat__category_fallback_Politics | 0.248039 |
| num__duration_hours | 0.350855 |
| num__log_volume | 0.370494 |
| cat__category_fallback_Sports | 0.560604 |
| num__market_implied_prob | 3.143656 |



## 6. Current monitor outputs

# Current Monitor Report

## Filters used

- Polymarket: trained current scorer with current-market feature filters already applied.
- Kalshi: current binary markets, non-combo products, 6 <= time_to_close_hours <= 336, volume_num > 0, open_interest_num > 0, volume_num >= 10.

## Caveats

- Polymarket scores are closer to the model's training domain.
- Kalshi scores are exploratory cross-venue outputs using a Polymarket-trained model.
- Kalshi rows are split into high-confidence and exploratory bands based on time-to-close, volume, and open interest.
- Large edges on low-volume or poorly categorized rows should be treated cautiously.


## Top 20 Polymarket edges

| venue | question | category_fallback | time_to_close_hours | volume | market_implied_prob | model_prob | model_minus_market | abs_edge | direction | edge_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Polymarket | Will the next Prime Minister of Hungary be Péter Magyar? | Other | 623.1092414025 | 3490346.5433069677 | 0.645 | 0.8061441121585599 | 0.16114411215855984 | 0.16114411215855984 | bullish_vs_market | large |
| Polymarket | Will Sweden qualify for the 2026 FIFA World Cup? | Sports | 623.1092414025 | 107805.19855699979 | 0.275 | 0.1251999538796041 | -0.14980004612039594 | 0.14980004612039594 | bearish_vs_market | medium |
| Polymarket | Will Ukraine qualify for the 2026 FIFA World Cup? | Sports | 623.1092414025 | 140899.94874300045 | 0.27 | 0.12389865095650375 | -0.14610134904349625 | 0.14610134904349625 | bearish_vs_market | medium |
| Polymarket | BitBoy convicted? | Other | 347.1092414025 | 107344.16603599946 | 0.1795 | 0.03882978347109298 | -0.14067021652890702 | 0.14067021652890702 | bearish_vs_market | medium |
| Polymarket | Will Italy qualify for the 2026 FIFA World Cup? | Sports | 623.1092414025 | 222351.13500099987 | 0.64 | 0.7462580114496247 | 0.10625801144962466 | 0.10625801144962466 | bullish_vs_market | medium |
| Polymarket | Will Scottie Scheffler win the 2026 Masters tournament? | Sports | 647.1092414025 | 93911.88471300004 | 0.185 | 0.08145778686599615 | -0.10354221313400384 | 0.10354221313400384 | bearish_vs_market | medium |
| Polymarket | Will Poland qualify for the 2026 FIFA World Cup? | Sports | 623.1092414025 | 461478.0072570008 | 0.355 | 0.25300070379150835 | -0.10199929620849163 | 0.10199929620849163 | bearish_vs_market | medium |
| Polymarket | Will the next Prime Minister of Hungary be Viktor Orbán? | Other | 623.1092414025 | 3044411.392079016 | 0.345 | 0.24864472218855752 | -0.09635527781144246 | 0.09635527781144246 | bearish_vs_market | medium |
| Polymarket | Will the next Prime Minister of Hungary be István Kapitány? | Other | 623.1092414025 | 8601447.815215958 | 0.0035 | 0.06247414342289685 | 0.05897414342289685 | 0.05897414342289685 | bullish_vs_market | small |
| Polymarket | Will Rory McIlroy win the 2026 Masters tournament? | Sports | 647.1092414025 | 71975.08676300007 | 0.085 | 0.033967807022226446 | -0.05103219297777356 | 0.05103219297777356 | bearish_vs_market | small |
| Polymarket | Will the next Prime Minister of Hungary be János Lázár? | Other | 623.1092414025 | 2165498.949212005 | 0.003 | 0.04946639980960465 | 0.046466399809604646 | 0.046466399809604646 | bullish_vs_market | small |
| Polymarket | Will Shane Lowry win the 2026 Masters tournament? | Sports | 647.1092414025 | 6454162.086943021 | 0.0145 | 0.050798737512527004 | 0.036298737512527005 | 0.036298737512527005 | bullish_vs_market | small |
| Polymarket | Will Jason Day win the 2026 Masters tournament? | Sports | 647.1092414025 | 3431641.7789369943 | 0.0135 | 0.041630138502578885 | 0.028130138502578887 | 0.028130138502578887 | bullish_vs_market | small |
| Polymarket | Will Viktor Hovland win the 2026 Masters tournament? | Sports | 647.1092414025 | 4816143.956149003 | 0.019 | 0.04629065836722524 | 0.027290658367225242 | 0.027290658367225242 | bullish_vs_market | small |
| Polymarket | Will Robert MacIntyre win the 2026 Masters tournament? | Sports | 647.1092414025 | 3623984.788885994 | 0.018 | 0.043522354613517125 | 0.025522354613517127 | 0.025522354613517127 | bullish_vs_market | small |
| Polymarket | Will Tyrrell Hatton win the 2026 Masters tournament? | Sports | 647.1092414025 | 2198871.010930997 | 0.0125 | 0.037942747061843446 | 0.025442747061843445 | 0.025442747061843445 | bullish_vs_market | small |
| Polymarket | Will Adam Scott win the 2026 Masters tournament? | Sports | 647.1092414025 | 1563943.9889379998 | 0.01 | 0.03497712410176722 | 0.024977124101767216 | 0.024977124101767216 | bullish_vs_market | small |
| Polymarket | Will Tiger Woods win the 2026 Masters tournament? | Sports | 647.1092414025 | 468089.62181399943 | 0.0035 | 0.02780158498137702 | 0.02430158498137702 | 0.02430158498137702 | bullish_vs_market | small |
| Polymarket | Will Matt Fitzpatrick win the 2026 Masters tournament? | Sports | 647.1092414025 | 2190260.265654002 | 0.0195 | 0.042165584941374235 | 0.022665584941374235 | 0.022665584941374235 | bullish_vs_market | small |
| Polymarket | Will the next Prime Minister of Hungary be Klára Dobrev? | Other | 623.1092414025 | 3723936.991883979 | 0.0015 | 0.024078310919266176 | 0.022578310919266174 | 0.022578310919266174 | bullish_vs_market | small |



## Top 20 Kalshi high-confidence edges

| venue | question | category_fallback | time_to_close_hours | volume_num | market_implied_prob | model_prob | model_minus_market | abs_edge | direction | edge_bucket | confidence_band |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kalshi | SOL price  on Mar 20, 2026? | Crypto | 64.2661261125 | 423.0 | 0.61 | 0.1587877618583127 | -0.4512122381416873 | 0.4512122381416873 | bearish_vs_market | large | high_confidence |
| Kalshi | SOL price  on Mar 20, 2026? | Crypto | 64.2661261125 | 603.0 | 0.49 | 0.06097566194106306 | -0.4290243380589369 | 0.4290243380589369 | bearish_vs_market | large | high_confidence |
| Kalshi | Ethereum price at Mar 20, 2026 at 5pm EDT? | Crypto | 64.2661261125 | 970.0 | 0.62 | 0.1960905885153388 | -0.4239094114846612 | 0.4239094114846612 | bearish_vs_market | large | high_confidence |
| Kalshi | SOL price  on Mar 20, 2026? | Crypto | 64.2661261125 | 501.0 | 0.6599999999999999 | 0.24001963378494187 | -0.4199803662150581 | 0.4199803662150581 | bearish_vs_market | large | high_confidence |
| Kalshi | SOL price  on Mar 20, 2026? | Crypto | 64.2661261125 | 1377.0 | 0.49 | 0.07075483193609228 | -0.4192451680639077 | 0.4192451680639077 | bearish_vs_market | large | high_confidence |
| Kalshi | Ethereum price at Mar 20, 2026 at 5pm EDT? | Crypto | 64.2661261125 | 2937.0 | 0.525 | 0.10782070060571368 | -0.41717929939428633 | 0.41717929939428633 | bearish_vs_market | large | high_confidence |
| Kalshi | SOL price  on Mar 20, 2026? | Crypto | 64.2661261125 | 261.0 | 0.42500000000000004 | 0.03287812598545396 | -0.39212187401454607 | 0.39212187401454607 | bearish_vs_market | large | high_confidence |
| Kalshi | Bitcoin price  on Mar 20, 2026? | Crypto | 64.2661261125 | 8339.0 | 0.47 | 0.08493349982873617 | -0.3850665001712638 | 0.3850665001712638 | bearish_vs_market | large | high_confidence |
| Kalshi | Ethereum price at Mar 20, 2026 at 5pm EDT? | Crypto | 64.2661261125 | 1873.0 | 0.435 | 0.05083617362214283 | -0.3841638263778572 | 0.3841638263778572 | bearish_vs_market | large | high_confidence |
| Kalshi | Bitcoin price  on Mar 20, 2026? | Crypto | 64.2661261125 | 17116.0 | 0.52 | 0.13928741347477305 | -0.380712586525227 | 0.380712586525227 | bearish_vs_market | large | high_confidence |
| Kalshi | Will MONICA have At Least 3000 pure album sales on the Hits Daily Double Top 50 Chart for March 19th 2026? | Culture/Entertainment | 47.24945944583334 | 120.0 | 0.475 | 0.09510775506491378 | -0.3798922449350862 | 0.3798922449350862 | bearish_vs_market | large | high_confidence |
| Kalshi | Will the gold open price be above $5009.99 on Mar 20, 2026 at 5pm EDT? | Macro/Commodities | 64.2661261125 | 97.0 | 0.5549999999999999 | 0.1776020147641161 | -0.37739798523588386 | 0.37739798523588386 | bearish_vs_market | large | high_confidence |
| Kalshi | Will the WTI front-month settle oil price  be >95.99 on Mar 18, 2026? | Macro/Commodities | 13.7661261125 | 170.0 | 0.51 | 0.13394731080546365 | -0.3760526891945364 | 0.3760526891945364 | bearish_vs_market | large | high_confidence |
| Kalshi | Will the WTI front-month settle oil price  be >100.99 on Mar 18, 2026? | Macro/Commodities | 13.7661261125 | 176.0 | 0.495 | 0.11987202622453952 | -0.3751279737754605 | 0.3751279737754605 | bearish_vs_market | large | high_confidence |
| Kalshi | Will the WTI front-month settle oil price  be >96.99 on Mar 18, 2026? | Macro/Commodities | 13.7661261125 | 285.0 | 0.495 | 0.12999328412265768 | -0.36500671587734235 | 0.36500671587734235 | bearish_vs_market | large | high_confidence |
| Kalshi | Will the WTI front-month settle oil price  be >93.99 on Mar 18, 2026? | Macro/Commodities | 13.7661261125 | 267.0 | 0.515 | 0.1503887717507383 | -0.36461122824926173 | 0.36461122824926173 | bearish_vs_market | large | high_confidence |
| Kalshi | What will Donald Trump say during Shamrock Bowl Presentation? | Politics | 9.2661261125 | 53.0 | 0.46 | 0.09644924537081231 | -0.36355075462918773 | 0.36355075462918773 | bearish_vs_market | large | high_confidence |
| Kalshi | What will any participating contestant say during Survivor Season 50 Episode 4? | Culture/Entertainment | 33.2661261125 | 133.0 | 0.575 | 0.21167772654262956 | -0.3633222734573704 | 0.3633222734573704 | bearish_vs_market | large | high_confidence |
| Kalshi | Will the WTI front-month settle oil price  be >97.99 on Mar 18, 2026? | Macro/Commodities | 13.7661261125 | 355.0 | 0.49 | 0.13054654566971205 | -0.35945345433028797 | 0.35945345433028797 | bearish_vs_market | large | high_confidence |
| Kalshi | Will there be at least 7 presidential actions in the week of Mar 15, 2026? | Politics | 105.26612611249999 | 54.0 | 0.44999999999999996 | 0.09192821127470348 | -0.3580717887252965 | 0.3580717887252965 | bearish_vs_market | large | high_confidence |



## Top 20 Kalshi exploratory edges

| venue | question | category_fallback | time_to_close_hours | volume_num | market_implied_prob | model_prob | model_minus_market | abs_edge | direction | edge_bucket | confidence_band |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kalshi | Will the WTI front-month settle oil price  be >92.99 on Mar 18, 2026? | Macro/Commodities | 13.7661261125 | 14.0 | 0.51 | 0.08816392711549438 | -0.42183607288450564 | 0.42183607288450564 | bearish_vs_market | large | exploratory |
| Kalshi | What will any participating contestant say during Survivor Season 50 Episode 4? | Culture/Entertainment | 33.2661261125 | 44.0 | 0.5 | 0.09546736876215088 | -0.4045326312378491 | 0.4045326312378491 | bearish_vs_market | large | exploratory |
| Kalshi | Will the silver open price be above $82.49 on Mar 20, 2026 at 5pm EDT? | Macro/Commodities | 64.2661261125 | 30.0 | 0.49 | 0.0862797278768374 | -0.4037202721231626 | 0.4037202721231626 | bearish_vs_market | large | exploratory |
| Kalshi | SOL price  on Mar 20, 2026? | Crypto | 64.2661261125 | 204.0 | 0.7250000000000001 | 0.3320984362575775 | -0.3929015637424226 | 0.3929015637424226 | bearish_vs_market | large | exploratory |
| Kalshi | What will Tulsi Gabbard say during House Intelligence Committee: hearing on the 2026 Annual Worldwide Threats Assessment? | Politics | 9.2661261125 | 23.0 | 0.515 | 0.12461603208587527 | -0.3903839679141248 | 0.3903839679141248 | bearish_vs_market | large | exploratory |
| Kalshi | What will Trey the Triceratops (Sub-Adult Triceratops Skeleton) go for at auction? | Other | 335.24945944583334 | 31.0 | 0.495 | 0.11687691486710748 | -0.3781230851328925 | 0.3781230851328925 | bearish_vs_market | large | exploratory |
| Kalshi | Evan Mobley: Double Double | Other | 331.2661261125 | 40.0 | 0.51 | 0.13206313075255177 | -0.37793686924744824 | 0.37793686924744824 | bearish_vs_market | large | exploratory |
| Kalshi | Venezuela vs USA first 5 innings runs? | Sports | 43.266126112500004 | 10.0 | 0.505 | 0.1323702737427695 | -0.3726297262572305 | 0.3726297262572305 | bearish_vs_market | large | exploratory |
| Kalshi | What will Kash Patel say during House Intelligence Committee: hearing on the 2026 Annual Worldwide Threats Assessment? | Politics | 9.2661261125 | 19.0 | 0.585 | 0.21254221916831456 | -0.3724577808316854 | 0.3724577808316854 | bearish_vs_market | large | exploratory |
| Kalshi | Will UST Par Yield Curve (30Y) for Q1 2026 be above 4.90%? | Macro/Commodities | 326.74945944583334 | 42.0 | 0.43 | 0.06467044383686237 | -0.3653295561631376 | 0.3653295561631376 | bearish_vs_market | large | exploratory |
| Kalshi | Will UST Par Yield Curve (10Y) for Q1 2026 be above 3.60%? | Macro/Commodities | 326.74945944583334 | 200.0 | 0.5 | 0.13580052138103868 | -0.3641994786189613 | 0.3641994786189613 | bearish_vs_market | large | exploratory |
| Kalshi | Will UST Par Yield Curve (10Y) for Q1 2026 be above 3.40%? | Macro/Commodities | 326.74945944583334 | 201.0 | 0.5 | 0.13591298708947017 | -0.3640870129105298 | 0.3640870129105298 | bearish_vs_market | large | exploratory |
| Kalshi | Will the B200 compute per hour price be above $3.22 on Mar 31? | Other | 335.26584833472225 | 22.0 | 0.5800000000000001 | 0.21910977443293964 | -0.3608902255670604 | 0.3608902255670604 | bearish_vs_market | large | exploratory |
| Kalshi | Will the A100 SXM4 compute per hour price be above $0.89 on Mar 31? | Other | 335.26584833472225 | 16.0 | 0.595 | 0.23422984205537217 | -0.3607701579446278 | 0.3607701579446278 | bearish_vs_market | large | exploratory |
| Kalshi | Detroit vs Pittsburgh Winner? | Sports | 65.34945944583333 | 18.0 | 0.5 | 0.1398390168875633 | -0.3601609831124367 | 0.3601609831124367 | bearish_vs_market | large | exploratory |
| Kalshi | Kansas City vs Texas Winner? | Sports | 68.34945944583333 | 12.0 | 0.45999999999999996 | 0.10078830063000253 | -0.3592116993699974 | 0.3592116993699974 | bearish_vs_market | large | exploratory |
| Kalshi | Will Jacob Fearnley win the Damm Jr vs Fearnley : Round Of 128 match? | Sports | 322.2661261125 | 16.0 | 0.505 | 0.14723752733382195 | -0.35776247266617806 | 0.35776247266617806 | bearish_vs_market | large | exploratory |
| Kalshi | Oklahoma City at Orlando: Total Points | Sports | 330.2661261125 | 16.0 | 0.51 | 0.1533853199231253 | -0.3566146800768747 | 0.3566146800768747 | bearish_vs_market | large | exploratory |
| Kalshi | Will UST Par Yield Curve (10Y) for Q1 2026 be above 3.80%? | Macro/Commodities | 326.74945944583334 | 200.0 | 0.53 | 0.17345268728549562 | -0.3565473127145044 | 0.3565473127145044 | bearish_vs_market | large | exploratory |
| Kalshi | Will there be at least 8 presidential actions in the week of Mar 15, 2026? | Politics | 105.26612611249999 | 42.0 | 0.435 | 0.07944122832170684 | -0.35555877167829314 | 0.35555877167829314 | bearish_vs_market | large | exploratory |



## 7. Interpretation

- Offline results suggest the model adds the most value close to resolution.
- The 24h snapshot beats both naive and market baselines in the current evaluation summary.
- Current Polymarket outputs are the most presentation-ready monitor leg.
- Kalshi outputs are useful for exploratory discrepancy ranking, especially after filtering and confidence banding, but still show many suspicious extremes.

## 8. Caveats

- Cross-venue scoring from a Polymarket-trained model to Kalshi is not a fully validated production setup.
- Large edges on low-volume or lower-confidence rows should not be treated as strong signals without additional review.
- Category heuristics are still lightweight and may misclassify some contracts.

## 9. Recommended next steps

- Add venue-specific historical training for Kalshi if historical data becomes available.
- Tighten or tier Kalshi confidence rules further.
- Add a lightweight dashboard or automated point-in-time export.
- Continue monitoring calibration and Brier Skill Score as the feature set evolves.
