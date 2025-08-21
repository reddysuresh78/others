from utils import filter_spans_by_trace_criteria, prepare_trace_data_for_evaluation, extract_tool_calls, TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE
from arize.exporter import ArizeExportClient
from arize.utils.types import Environments
from datetime import datetime, timedelta, timezone
from phoenix.evals import llm_classify, OpenAIModel
import nest_asyncio, os
import pandas as pd

nest_asyncio.apply()
 
api_key = "ak-1f3268bf-71eb-4c11-9f8a-03120cf07220-NIwX1qCewFjujYpO6eSAyV_2-YUHyUEM"
project_name = "Suresh_test"

os.environ['ARIZE_API_KEY'] = api_key

client = ArizeExportClient(api_key=os.environ['ARIZE_API_KEY'])
 
primary_df = client.export_model_to_df(
    space_id = "U3BhY2U6MjYxODI6cUlwUg==",
    model_id="Suresh_test",  #Project name
    environment = Environments.TRACING,
    start_time = datetime.now(timezone.utc) - timedelta(days=7),
    end_time   = datetime.now(timezone.utc),
    # where = "\"name\" = 'suresh_eval_calc_test'"
)
    
print('#### Exporting your primary dataset into a dataframe.')
 

eval_traces = filter_spans_by_trace_criteria(
    df=primary_df,
    trace_filters={"name": {"contains": "suresh"}},
    span_filters={"attributes.openinference.span.kind": {"==": "LLM"}}
)

eval_traces['tool_calls'] = eval_traces['attributes.llm.output_messages'].apply(extract_tool_calls)

print(eval_traces[['tool_calls']].head())

trajectories = [
    {
    "user_question": "To calculate the value of an expression", 
    "trajectory": {"1":"calculate"}
    }, 
    {
    "user_question": "To calculate the weather of a city", 
    "trajectory": {"1":"get_weather"}
    }
                     
]

info = []
for trajectory in trajectories:
    info.append(f"""User's Question: {trajectory["user_question"]} \nTrajectory:{trajectory["trajectory"]}""")
    


tool_calls_df = prepare_trace_data_for_evaluation(
    df=eval_traces,
    extract_cols={"tool_calls": "tool_calls", "attributes.llm.tools": "attributes.llm.tools", "attributes.input.value":"attributes.input.value"}, #can also add any additional columns to the dataframe
    additional_data={"reference_outputs": "\n".join(info) },
)

print(tool_calls_df.head())

sample_data = tool_calls_df.head(2)

print(sample_data.head())

 
model = OpenAIModel(
    api_key=os.environ['OPENAI_API_KEY'],
    model="gpt-4o-mini",
    temperature=0.0,
)

rails =["correct","incorrect"]
eval_results = llm_classify(
    dataframe=sample_data,
    template=TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
    model=model,
    rails=rails,
    include_prompt=True, 

    provide_explanation=True,
    verbose=False,
    concurrency=20,
)

eval_results.to_csv("results.csv")

print(eval_results.head())