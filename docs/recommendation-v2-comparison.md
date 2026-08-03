# Recommendation V2 comparison and acceptance record

## Scope

This report compares the fixed offline profiles used by
`docs/recommendation-v1-baseline.md` with the V2 implementation exposed by the
`recommendation_service.py` Facade and implemented in
`backend/app/services/recommendation_core/`. It is an engineering
regression report, not a nutrition or market-price evaluation.

The run uses the 24 fruits in `data/fruits_seed.json`, month 7, region `华东`,
and `random_seed=20260731`. The V2 run uses the new identity, role, display-group and portion
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

> This seven-profile summary was regenerated with the current semantic-correction
> code. The complete top-10 lists are in the next section.

| Profile | V1 pair | V2 pair | V2 total score | Notes |
| --- | --- | --- | ---: | --- |
| low budget / crisp / convenient | 芒果 + 榴莲 | 苹果 + 木瓜 | 0.6103 | above-budget fruit receives a lower utility |
| sour-sweet / accepts cutting | 芒果 + 榴莲 | 苹果 + 木瓜 | 0.6386 | taste, price and pair terms are scored together |
| sweet / soft / higher budget | 芒果 + 榴莲 | 芒果 + 榴莲 | 0.6668 | explicit taste match can make a tropical pair competitive |
| mango forbidden | 木瓜 + 榴莲 | 木瓜 + 苹果 | 0.6372 | forbidden mango is removed before scoring |
| recently ate mango | 木瓜 + 榴莲 | 木瓜 + 苹果 | 0.6372 | recent history lowers mango freshness |
| not tried avocado and durian | 葡萄 + 木瓜 | 葡萄 + 木瓜 | 0.6362 | level 1 does not allow both explicit unfamiliar fruits |
| cold start / no explicit preference | 葡萄 + 木瓜 | 葡萄 + 木瓜 | 0.6362 | default profile remains deterministic |

The exact current individual scores for representative rows are:

- low budget: 苹果 `0.6174`, 木瓜 `0.5423`;
- sour-sweet: 桃 `0.6703`, 葡萄 `0.6701`;
- sweet/soft: 芒果 `0.6968`, 榴莲 `0.6815`;
- unfamiliar level 1: 葡萄 `0.6636`, 木瓜 `0.6328`.

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
| low budget / crisp / convenient | 香蕉 .6360; 西瓜 .6205; 苹果 .6174; 桃 .6002; 梨 .5981; 葡萄 .5957; 橘子 .5898; 龙眼 .5747; 橙子 .5642; 蓝莓 .5640 | 苹果 + 木瓜 | .6103 |
| sour-sweet / accepts cutting | 桃 .6703; 葡萄 .6701; 菠萝 .6559; 西瓜 .6525; 龙眼 .6496; 哈密瓜 .6434; 香蕉 .6425; 芒果 .6423; 蓝莓 .6306; 火龙果 .6260 | 苹果 + 木瓜 | .6386 |
| sweet / soft / higher budget | 西瓜 .7165; 桃 .7144; 香蕉 .7096; 荔枝 .7003; 龙眼 .6980; 芒果 .6968; 哈密瓜 .6920; 葡萄 .6886; 木瓜 .6854; 榴莲 .6815 | 芒果 + 榴莲 | .6668 |
| mango forbidden | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 龙眼 .6540; 哈密瓜 .6480; 火龙果 .6401; 菠萝 .6381; 木瓜 .6328; 蓝莓 .6237 | 木瓜 + 苹果 | .6372 |
| recently ate mango | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 龙眼 .6540; 哈密瓜 .6480; 芒果 .6403; 火龙果 .6401; 菠萝 .6381; 木瓜 .6328 | 木瓜 + 苹果 | .6372 |
| not tried avocado and durian | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 龙眼 .6540; 哈密瓜 .6480; 芒果 .6448; 火龙果 .6401; 菠萝 .6381; 木瓜 .6328 | 葡萄 + 木瓜 | .6362 |
| cold start / no explicit preference | 桃 .6751; 西瓜 .6640; 葡萄 .6636; 香蕉 .6586; 龙眼 .6540; 哈密瓜 .6480; 芒果 .6448; 火龙果 .6401; 菠萝 .6381; 木瓜 .6328 | 葡萄 + 木瓜 | .6362 |

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
- `display_group` is a consumer-facing directory label only. It is not read by
  single-fruit scoring, pair scoring, nutrition, season, history, or exploration
  rules. The compatibility field `category` is deprecated.
- `sensory_category_diversity` keeps its public name for compatibility but now
  means the average absolute difference of sweet, sour, soft, and crisp scores.
- Static `exploration` roles are no longer valid. Exploration is a per-user
  state derived from `has_tried`, `willing_to_try`, and `discovery_level`.

## Verification

- Backend: `207 passed, 30 skipped` with the repository's Python 3.11 environment.
- Frontend: `npm test` passed (23 Node tests, 25 component tests).
- Frontend production build: `npm run build` passed.
- Remote Supabase project `Daily Fruit` is at migration version `0009`; read-only
  verification found 24 active fruits, 23 `main`, one `supporting`, complete
  display groups, 24 nutrition rows and 48 season rows. RLS remains enabled with
  no policies, and the existing security-advisor warning is outside this task.
- The V2 seed ran twice after migration; both runs kept 24/24/48 rows and
  unique natural keys.
- `backend/tests/services/test_fixed_profiles_v2.py` rebuilds the seven fixed
  profiles from the seed files and checks top-10 ordering, two-item uniqueness,
  explanation count, forbidden-fruit filtering and the unfamiliar-pair rule.
