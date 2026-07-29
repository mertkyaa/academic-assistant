import anthropic
from config import ANTHROPIC_API_KEY,ACTIVE_MODEL,validate_config

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TOOLS = [
    {
        "name": "search_papers",
        "description": "Search for academic papers on arXiv. Returns papers for a given topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic or keyword to search. e.g. 'reinforcement learning'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of papers to return. Default: 5"
                }
            },
            "required": ["query"]
        }
    }
]

def search_papers(query: str, max_results: int = 5) -> list:
    print(f" [Tool called] search_papers(query='{query})', max_result={max_results})")

    mock_result  = [
        {
            "id": "2301.04567",
            "title": f"Advance in {query}: A Comprehensive Survey",
            "authors": ["Smith, J.", "Doe, A."],
            "abstract": f"This paper surveys recent developments in {query}",
            "url": "https://arxiv.org/abs/2301.04567"
        },
        {
            "id": "2302.09876",
            "title": f"Practical Applications of {query}",
            "authors": ["Chen, L.", "Kumar, P."],
            "abstract": f"We present empirical results from applying {query}...",
            "url": "https://arxiv.org/abs/2302.09876"
        }
    ]
    return mock_result[:max_results]


def execute_tool(tool_name: str, tool_input: dict):
    if tool_name == "search_papers":
        return search_papers(**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}
    
def run_agent(user_message: str) -> str:
    print(f"\nUser: {user_message}\n")

    messages = [
        {"role": "user", "content": user_message}

    ]

    while True:
        response = client.messages.create(
            model=ACTIVE_MODEL,
            max_tokens=1024,
            system="You are an academix reasearch assistant. Help users find and understand research papers ",
            tools= TOOLS,
            messages= messages
        )

        print (f" Claude decision: stop reason='{response.stop_reason}'")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})


            tool_result = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f" Claude wants to call: {block.name}({block.input})")
                    result = execute_tool(block.name,block.input)
                    tool_result.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })
            messages.append({"role": "user", "content": tool_result})


        elif response.stop_reason == "end_turn":
            final_text = response.content[0].text
            print(f"\nAssistant: {final_text}")
            return final_text


if __name__ == "__main__":
    run_agent("Find me papers about reinforcement learning agents.")            