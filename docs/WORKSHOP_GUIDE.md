# Hands-on workshop guide

## Suggested demonstration order

1. Show `normal_llm01.py` and `normal_llm02.py`: remote model and conversation history.
2. Execute `00_rule_based_math.py` and `00_rule_based_inventory.py`: Python controls all computations.
3. Execute `01_normal_llm_math.py` and `01_normal_llm_inventory.py`: send prompt, parse answer, discuss verification limits.
4. Execute `02_agentic_math_tools.py` and `02_agentic_tools_inventory.py`: inspect tool request, `FUNCTIONS` dispatch, and returned tool message.
5. Execute `03_graph_harness_math.py` and `03_graph_harness_inventory.py`: decision, validation, execution, state update, retry, skip.

## Suggested learner observations

For each demo ask: **Who decides the next step? Who actually executes it? What input is validated? Is the final answer independently verified?**

## Inventory CSV columns

`product_id,name,category,quantity,minimum_stock,price` — prices represent example EGP/unit. Valid numbers must be nonnegative; quantity and minimum stock are nonnegative whole numbers.

## Failure exercises

- Original `P003` has `price=X`: compare immediate skip (Approach 2 inventory) with three trials (Approach 3 inventory).
- In the graph inventory script, run `--trace YES`; before the next attempt, edit price in `inventory.csv`, save, then press Enter. The row is reread.
- For calculator demos, try `--expression "12 + 8 * 3 - 10 / 0"`; discuss exception handling and retry limits. Do not assume all demos recover identically.
- Explore how tool selection may differ across model calls, even with the same prompt.

## Instructor checklist

- Provide each attendee their own API key and internet access.
- Run offline tests first: `python tests/smoke_test.py`.
- Avoid exposing `.env` or posting console traces containing credentials.
- Leave extra time for rate limits and interactive Enter checkpoints.
- Reset `inventory.csv` from the original repository before repeating the invalid-input exercise.

## GitHub publishing steps

1. Create a new **public** GitHub repository.
2. Extract the workshop ZIP; upload the **contents of its folder** to the repository root (or use `git init`, `git add .`, `git commit`, and `git push`).
3. Confirm `.env` does not exist in the published repository. `.env.example` is safe.
4. Share the repository link. Attendees use **Code → Download ZIP** or `git clone`.
5. Ask attendees to make their own `.env` file locally after download.
