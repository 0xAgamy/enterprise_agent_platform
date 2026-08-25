from fastmcp import Client

async def get_tool_descriptions_from_mcp_servers(mcp_servers: list[str]) -> list[dict]:
    tool_descriptions = []

    for server in mcp_servers:
        client = Client(server)

        async with client:
            tools = await client.list_tools()

            for tool in tools:
                result = {
                    "name": "",
                    "description": "",
                    "parameters": {"type": "object", "properties": {}},
                    "required": [],
                    "returns": {"type": "string", "description": ""},
                    "server": server,
                }

                result["name"] = tool.name
                result["required"] = tool.inputSchema.get("required", [])

                # Get Description
                description = tool.description.split("\n\n")[0]
                result["description"] = description

                # Get Returns
                returns = tool.outputSchema.get("result",[])
                result["returns"]["description"] = returns

                # Get Parameters
                properties = tool.inputSchema.get("properties", {})

            

                result["parameters"]["properties"] = properties

                tool_descriptions.append(result)

    return tool_descriptions
