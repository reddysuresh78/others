import os

from typing import Union

from autogen import ConversableAgent
from autogen import GroupChat
from autogen import GroupChatManager
from autogen import Agent
from autogen.coding import LocalCommandLineCodeExecutor
 
from pathlib import Path
import subprocess

import os

def get_latest_file(directory):
    # Get a list of files in the directory
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    
    if not files:
        return None  # No files in the directory
    
    # Get the latest file based on the modification time
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

# The Number Agent always returns the same numbers.
source_reader_agent = ConversableAgent(
    name="SourceReader_Agent",
    system_message="You return the final code after conversion.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)
   
# The Dependency Graph Generator Agent generates dependency graph based on the set of cobol files provided. 
code_analyzer_agent = ConversableAgent(
    name="CodeAnalyzer_Agent",
    system_message="""You are good at analyzing the source code in Cobol. 
    Your task is to emit pseudo code of each cobol file. Clearly mention the name of the cobol file in the output.
    """,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)
 
# The Dependency Graph Generator Agent generates dependency graph based on the set of cobol files provided. 
dep_graph_gen_agent = ConversableAgent(
    name="DependencyGraph_Agent",
    system_message="""You are good at analyzing the source code in Cobol and create dependency graph, sequence diagrams in mermaid notation. 
    Your task is to emit following python code for dependency diagrams and sequence diagrams after replacing appropriate place holders.
    Repeat following entire code block for each diagram with proper indentation.
    Do not emit anything other than python code inside ```.
    
    ```python
import mermaid as md
from mermaid.graph import Graph

notation=\"""#mermaid notation here\"""

sequence = Graph('Sequence-diagram', notation)
render = md.Mermaid(sequence)
render.to_png(# file name here with png extension)
    ``` 
    """,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)
 
work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)
 
# Create a local command line code executor.
executor = LocalCommandLineCodeExecutor(
    timeout=10,  # Timeout for each code execution in seconds.
    work_dir=work_dir,  # Use the temporary directory to store the code files.
)
 
# The Designer Agent designs the system based on dependency graph
diagram_creator_agent = ConversableAgent(
    name="DiagramCreator_Agent",
    llm_config=False,  # Turn off LLM for this agent.
    code_execution_config={"executor": executor},  # Use the local command line code executor.
    human_input_mode="None",  # Always take human input for this agent for safety.
)

# The Designer Agent designs the system based on dependency graph
designer_agent = ConversableAgent(
    name="Designer_Agent",
    system_message="""You are good at designing an object oriented python project based on the pseudo code and dependency graph. 
    Use your expertise designing a proper object oriented system by following all OOP principles and design patterns.
    You return the design with various Classes and what each class and method is supposed to do. If you don't have any changes in the design, just say DONE_FULLY. """,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)
 
# The Coder Agent generates source code based on the design.
coder_agent = ConversableAgent(
    name="Coder_Agent",
    system_message="""You are good at generating the source code and fix any review comments in Python based on the classes and methods described in the design/review comments. 
    Ensure the code follows all best practics like exception handling logging, comments, and complete set of test cases.
    You return the generated code along with the test cases. 
    If you don't have anything to code, just say DONE_FULLY. """,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)
 
# The Coder Agent generates source code based on the design.
code_reviewer_agent = ConversableAgent(
    name="CodeReviewer_Agent",
    system_message="You are good at reviewing the source code written in Python. You return the review comments and suggestions. If you don't have any suggestions, just say DONE_FULLY. ",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
) 
 
def migrator_speaker_selection_func(last_speaker: Agent, groupchat: GroupChat) -> Union[Agent, str, None]:
    content = groupchat.messages[-1]["content"]
    speaker = last_speaker.name
    # print("Selecting next speaker ", speaker) #, groupchat.messages[-1])
    
    if speaker == "CodeReviewer_Agent":
        if "DONE_FULLY" in content:
            return 'round_robin'
        else:
            return coder_agent
    else:
         return 'round_robin'
      

agents = [  code_analyzer_agent, dep_graph_gen_agent, diagram_creator_agent, designer_agent, coder_agent, code_reviewer_agent, source_reader_agent] 

constrained_graph_chat = GroupChat(
    agents=agents,
    messages=[],
    max_round=len(agents) + 2, 
    send_introductions=True,
    # speaker_selection_method='round_robin',
    speaker_selection_method=migrator_speaker_selection_func,
)

constrained_group_chat_manager = GroupChatManager(
    groupchat=constrained_graph_chat,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

# read file into a string
with open("./repomix-output.txt", "r") as f:
    file_content = f.read()
 
 
chat_result = source_reader_agent.initiate_chat(
    constrained_group_chat_manager,
    message="Here is the COBOL project content. \n " + file_content,
    summary_method="reflection_with_llm",
)
 
print(chat_result.summary)
  
file_name = get_latest_file(work_dir)
 
print(f"Executing the migrated code {file_name} now...")
 
subprocess.run([ "python", file_name], check=True )

