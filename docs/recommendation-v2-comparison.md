# Recommendation V2 comparison and acceptance record

## Scope

This report compares the fixed offline profiles used by
`docs/recommendation-v1-baseline.md` with the V2 implementation exposed by the
`recommendation_service.py` Facade and implemented in
`backend/app/services/recommendation_core/`. It is an engineering
regression report, not a nutrition or market-price evaluation.

The run uses the 24 fruits in `data/fruits_seed.json`, month 7, region `华东`,
and `random_seed=20260731`. The V2 run uses the new identity, role, portion
metadata,
convenience, familiarity, availability, and data-quality fields. The legacy
season CSV is enriched by the seed loader with an explicit region level,
availability score, and supply status until those CSV columns are authored
directly.

## Formula implemented

```text
U = 0.30 explicit_preference
  + 0.25 taste_match
  + 0.20 availability_and_season
  + 0.10 price_match
  + 0.10 convenience
  + 0.05 history_freshness
  + feedback_adjustment

Pair = 0.70 mean(U)
     + 0.15 nutrition_pair
     + 0.10 sensory_category_diversity
     + 0.05 pair_novelty
```

Nutrition is normalized against the complete active library as 0–1 unitless
demo indices with P05/P95 bounds; `default_portion_grams` is not used in this
calculation. Values missing from a profile stay missing and reduce pair
confidence. The price term is one-sided: a fruit at or
below the user's budget receives 1, while prices above the budget receive a
bounded penalty. History and feedback use date-based exponential decay.

## Fixed profile output

> This five-row summary was regenerated with the current V2 code. The
> authoritative seven-profile run with all V2 top-10 lists is in the next
> section; use that section for acceptance.

| Profile | V1 pair | V2 pair | V2 total score | Notes |
| --- | --- | --- | ---: | --- |
| cold start | 芒果 + 榴莲 | 葡萄 + 木瓜 | 0.7141 | default/common fruits win instead of a single exotic pair |
| low budget / crisp / convenient | 芒果 + 榴莲 | 苹果 + 木瓜 | 0.6710 | above-budget fruit receives a lower utility |
| sweet / soft / higher budget | 芒果 + 榴莲 | 桃 + 木瓜 | 0.7447 | taste and pair diversity both contribute |
| mango forbidden | 木瓜 + 榴莲 | 葡萄 + 木瓜 | 0.7141 | forbidden mango is removed before scoring |
| known-only discovery | 芒果 + 榴莲 | 葡萄 + 木瓜 | 0.7277 | all 24 fruits marked tried; discovery level 0 only permits known fruits |

The exact V2 individual scores for the first two rows are:

- cold start: 葡萄 `0.6636`, 木瓜 `0.6328`;
- low budget: 苹果 `0.6174`, 木瓜 `0.5423`;
- sweet/soft: 桃 `0.7144`, 木瓜 `0.6854`;
- known-only: 葡萄 `0.6810`, 木瓜 `0.6544`.

The result is no longer a greedy “top two base scores” selection: all legal
pairs are enumerated, then the pair objective is applied. A deterministic
seed chooses only inside the 0.03 near-optimal window.

## Seven-profile acceptance run

The following table is the authoritative V2 run for all seven fixed profiles
from the V1 baseline. It records the V2 base-score top 10 and the final pair;
fruit names and scores are from the 24-row demonstration dataset, not a claim
about real market or nutrition rankings.

| Profile | V2 base-score top 10 (high → low) | Final pair | Pair score |
| --- | --- | --- | ---: |
| low budget / crisp / convenient | 香蕉 .6360; 西瓜 .6205; 苹果 .6174; 桃 .6002; 梨 .5981; 葡萄 .5957; 柑橘 .5898; 橙子 .5642; 蓝莓 .5640; 哈密瓜 .5620 | 苹果 + 木瓜 | .6710 |
| sour-sweet / accepts cutting | 桃 .6703; 葡萄 .6701; 西瓜 .6525; 哈密瓜 .6434; 香蕉 .6425; 菠萝 .6319; 蓝莓 .6306; 龙眼 .6256; 苹果 .6204; 木瓜 .6201 | 葡萄 + 木瓜 | .7119 |
| sweet / soft / higher budget | 西瓜 .7165; 桃 .7144; 香蕉 .7096; 哈密瓜 .6920; 葡萄 .6886; 木瓜 .6854; 荔枝 .6763; 蓝莓 .6760; 龙眼 .6740; 芒果 .6728 | 桃 + 木瓜 | .7447 |
| mango forbidden | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 哈密瓜 .6480; 木瓜 .6328; 龙眼 .6300; 蓝莓 .6237; 火龙果 .6161; 菠萝 .6141 | 葡萄 + 木瓜 | .7141 |
| recently ate mango | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 哈密瓜 .6480; 木瓜 .6328; 龙眼 .6300; 蓝莓 .6237; 芒果 .6163; 火龙果 .6161 | 葡萄 + 木瓜 | .7141 |
| not tried avocado and durian | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 哈密瓜 .6480; 木瓜 .6328; 龙眼 .6300; 蓝莓 .6237; 芒果 .6208; 火龙果 .6161 | 葡萄 + 木瓜 | .7141 |
| cold start / no explicit preference | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 哈密瓜 .6480; 木瓜 .6328; 龙眼 .6300; 蓝莓 .6237; 芒果 .6208; 火龙果 .6161 | 葡萄 + 木瓜 | .7141 |

The “recently ate mango” profile uses a two-day-old history event and lowers
mango's history-freshness term. The “not tried” profile marks avocado and
durian as explicit unfamiliar fruits; discovery rules prevent both from being
selected together. Explicitly unknown familiarity remains neutral rather than
being treated as “tried”.

## What remains intentionally limited

- The seed values are structured demonstration annotations. They are not
  authoritative seasonal, nutrition, or price data.
- The current 48 season rows remain backward-compatible CSV rows; the loader
  assigns `national`/`area` and demonstration availability defaults. A later
  data-curation task can replace those defaults with sourced regional data.
- User familiarity is optional. Unknown answers are not treated as either
  “tried” or “forbidden”.

## Verification

- Backend: `197 passed, 30 skipped` with the repository's Python 3.11 environment.
- Frontend: `npm test` passed (23 Node tests, 25 component tests).
- Frontend production build: `npm run build` passed.
- Remote Supabase project `Daily Fruit`, ref `frzbbpocyzlqxljsrsiw`, is now at
  version `0005`; read-only verification found the V2 columns/checks, RLS
  enabled with zero policies, and unchanged 24/24/48/11/57/11/22/4 counts.
- The V2 seed ran twice after migration; both runs kept 24/24/48 rows and
  unique natural keys.
- `backend/tests/services/test_fixed_profiles_v2.py` rebuilds the seven fixed
  profiles from the seed files and checks top-10 ordering, two-item uniqueness,
  explanation count, forbidden-fruit filtering and the unfamiliar-pair rule.
