from phoenix.evals import (
    llm_classify,
    OpenAIModel # see https://docs.arize.com/phoenix/evaluation/evaluation-models
    # for a full list of supported models
)
import os
import pandas as pd

from datetime import datetime, timedelta

TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE = """
You are a helpful AI bot that checks whether an AI agent's internal trajectory is accurate and effective.

You will be given:
1. The agent's actual trajectory of tool calls
2. You will be given input data from a user that the agent used to make a decision
3. You will be given a tool call definition, what the agent used to make the tool call
4. You will be given a golden trajectory for various input questions that represents the ideal flows in normal use for given question

An accurate trajectory:
- Progresses logically from step to step
- Follows the golden trajectory where reasonable
- Shows a clear path toward completing a goal
- Is reasonably efficient (doesn't take unnecessary detours)

##

Golden Trajectory info:
{reference_outputs}

##

Actual Trajectory:
{tool_calls}

User Inputs:
{attributes.input.value}

Tool Definition:
{attributes.llm.tools}

##

- First identify the correct trajectory based on user's input 
- Compare the actual trajectory to the golden one: 
    - Highlight any major deviations
    - Determine whether the deviations are acceptable or harmful
    - Assess if the overall goal is still achieved effectively

Your response must be a single string, either `correct` or `incorrect`, and must not include any additional text.

- Respond with `correct` if the agent's trajectory adheres to the rubric and accomplishes the task effectively.
- Respond with `incorrect` if the trajectory is confusing, misaligned with the goal, inefficient, or does not accomplish the task.


"""

from typing import Dict, Any

def filter_spans_by_trace_criteria(
    df: pd.DataFrame,
    trace_filters: Dict[str, Dict[str, Any]],
    span_filters: Dict[str, Dict[str, Any]]
) -> pd.DataFrame:
    """Filter spans based on trace-level and span-level criteria.

    Args:
        df: DataFrame with trace data
        trace_filters: Dictionary of column names and filtering criteria for traces
                      Format: {"column_name": {"operator": value}}
                      Supported operators: ">=", "<=", "==", "!=", "contains", "notna", "isna"
        span_filters: Dictionary of column names and filtering criteria for spans
                     Format: {"column_name": {"operator": value}}
                     Same supported operators as trace_filters

    Returns:
        DataFrame with filtered spans from traces that match trace_filters
    """
    # Get all unique trace_ids
    all_trace_ids = set(df['context.trace_id'].unique())
    print(f"Total traces: {len(all_trace_ids)}")

    # Create a copy of the dataframe for filtering
    df_copy = df.copy()

    # Find traces matching the trace criteria
    traces_df = df_copy.copy()
    for column, criteria in trace_filters.items():
        if column not in traces_df.columns:
            print(f"Warning: Column '{column}' not found in dataframe")
            continue

        for operator, value in criteria.items():
            if operator == ">=":
                matching_spans = traces_df[traces_df[column] >= value]
            elif operator == "<=":
                matching_spans = traces_df[traces_df[column] <= value]
            elif operator == "==":
                matching_spans = traces_df[traces_df[column] == value]
            elif operator == "!=":
                matching_spans = traces_df[traces_df[column] != value]
            elif operator == "contains":
                matching_spans = traces_df[traces_df[column].str.contains(value, case=False, na=False)]
            elif operator == "isna":
                matching_spans = traces_df[traces_df[column].isna()]
            elif operator == "notna":
                matching_spans = traces_df[traces_df[column].notna()]
            else:
                print(f"Warning: Unsupported operator '{operator}' - skipping")
                continue

            traces_df = matching_spans

    matching_trace_ids = set(traces_df['context.trace_id'].unique())
    print(f"Found {len(matching_trace_ids)} traces matching trace criteria")

    if not matching_trace_ids:
        print("No matching traces found")
        return pd.DataFrame()

    # Filter to keep only rows from matching traces
    result_df = df[df['context.trace_id'].isin(matching_trace_ids)].copy()

    # Apply span filters
    for column, criteria in span_filters.items():
        if column not in result_df.columns:
            print(f"Warning: Column '{column}' not found in dataframe")
            continue

        for operator, value in criteria.items():
            if operator == ">=":
                result_df = result_df[result_df[column] >= value]
            elif operator == "<=":
                result_df = result_df[result_df[column] <= value]
            elif operator == "==":
                result_df = result_df[result_df[column] == value]
            elif operator == "!=":
                result_df = result_df[result_df[column] != value]
            elif operator == "contains":
                result_df = result_df[result_df[column].str.contains(value, case=False, na=False)]
            elif operator == "isna":
                result_df = result_df[result_df[column].isna()]
            elif operator == "notna":
                result_df = result_df[result_df[column].notna()]
            else:
                print(f"Warning: Unsupported operator '{operator}' - skipping")
                continue

    print(f"Final result: {len(result_df)} spans from {len(matching_trace_ids)} traces")
    return result_df

def prepare_trace_data_for_evaluation(
    df,
    group_by_col="context.trace_id",
    extract_cols={"tool_calls": "tool_calls"},
    additional_data=None,
    filter_empty=True,
):
    """
    Prepare trace data for evaluation by grouping, sorting by start_time, and extracting specified columns.

    Args:
        df: DataFrame containing trace data
        group_by_col: Column to group traces by (default: "context.trace_id")
        extract_cols: Dict mapping {output_key: source_column} to extract from each row
                     Can contain multiple columns to extract
        additional_data: Dict of additional data to include with each trace (default: None)
        filter_empty: Whether to filter out empty values (default: True)

    Returns:
        DataFrame with processed trace data ready for evaluation
    """
    # Group by specified column
    grouped = df.groupby(group_by_col)

    # Prepare results list
    results = []

    for group_id, group in grouped:
        # Always sort by start_time to ensure correct order
        group = group.sort_values("start_time")

        # Initialize a dict to store extracted data
        trace_data = {group_by_col: group[group_by_col].iloc[0]}

        # Extract and process each requested column
        for output_key, source_col in extract_cols.items():
            ordered_extracts = []
            # Iterate through rows as dictionaries to handle column names with dots
            for i, (_, row_data) in enumerate(group.reset_index(drop=True).iterrows()):
                # Convert row to dictionary for easier access
                row_dict = row_data.to_dict()
                value = row_dict.get(source_col)
                if not filter_empty or (value is not None and value):
                    ordered_extracts.append({str(i + 1): value})
            trace_data[output_key] = ordered_extracts

        # Add any additional data
        if additional_data:
            trace_data.update(additional_data)

        # Add to results
        results.append(trace_data)

    # Convert to DataFrame
    return pd.DataFrame(results)

def extract_tool_calls(output_messages):
    if not output_messages:
        return []

    tool_calls = []
    for message in output_messages:
        if "message.tool_calls" in message:
            for tool_call in message["message.tool_calls"]:
                tool_calls.append({
                    "name": tool_call["tool_call.function.name"],
                    "arguments": tool_call["tool_call.function.arguments"]
                })
    return tool_calls

