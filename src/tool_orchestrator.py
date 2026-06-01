"""
ToolOrchestrator — ReAct tool loop with anti-loop protection and smart chaining.
"""

import re
import json
import asyncio
from src.logger import AppLogger, Colors

app_logger = AppLogger(__name__)


async def run_tool_loop(
    messages,
    initial_response,
    user_msg,
    brain,
    plugin_manager,
    context_mgr,
    metrics,
):
    """
    Advanced ReAct Orchestrator.
    Coordinates tool execution, handles automatic chaining, and prevents infinite loops.
    Returns: (response, execution_steps, extracted_sources, usage)
    """
    messages = list(messages)  # Work on a copy to avoid mutating caller's list
    MAX_TOOL_STEPS = 10
    tool_step = 0
    execution_steps = []
    extracted_sources = {}
    response = initial_response
    usage = None

    # Anti-Loop Registry: (tool_name, args_hash) -> count
    call_registry = {}

    while tool_step < MAX_TOOL_STEPS:
        tool_triggered = False
        tool_context = None
        current_step = {"step": tool_step + 1, "tool": None, "query": None, "result_summary": None}

        # 1. Parse response for tool calls
        is_tool, valid_calls, clean_response = brain.process_response(response)

        if not is_tool or not valid_calls:
            break  # Final response reached

        tool_name = valid_calls[0][0]
        tool_args = valid_calls[0][1]

        # 2. Anti-Loop Check
        args_str = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
        call_key = (tool_name, args_str)
        call_registry[call_key] = call_registry.get(call_key, 0) + 1

        if call_registry[call_key] > 2:
            tool_context = f"[SYSTEM ERROR] Loop detected: Tool {tool_name} called too many times with same args. Stop and provide a final answer based on available info."
            tool_triggered = True
        elif tool_name not in plugin_manager.tools:
            tool_context = f"[SYSTEM ERROR] Tool {tool_name} not found. Available: {list(plugin_manager.tools.keys())}"
            tool_triggered = True
        else:
            # 3. Execution
            print(f"{Colors.YELLOW}[*] Step {tool_step+1}: Executing {tool_name}({args_str[:50]}...){Colors.END}")
            try:
                result = await plugin_manager.execute_tool(tool_name, args_str)

                try:
                    json.loads(result)
                    metrics.record_parse_success(True)
                except Exception:
                    metrics.record_parse_success(False)

                # 4. Smart Chaining (Dependency Resolution)
                if isinstance(result, str) and any(x in tool_name.upper() for x in ["SEARCH", "FIND", "DISCOVER"]):
                    found_urls = re.findall(r'URL: (https?://[^\s\n\]]+)', result)
                    if found_urls:
                        print(f"{Colors.GREEN}[*] Dependency found: {len(found_urls)} URLs to read in parallel...{Colors.END}")
                        tasks = [plugin_manager.execute_tool("WEB_READ", url) for url in found_urls[:3]]
                        web_contents = await asyncio.gather(*tasks, return_exceptions=True)

                        chained_data = []
                        for i, content in enumerate(web_contents):
                            if isinstance(content, Exception):
                                chained_data.append(f"\n--- SOURCE {i+1}: {found_urls[i]} ---\n[ERROR: {content}]")
                            else:
                                chained_data.append(f"\n--- SOURCE {i+1}: {found_urls[i]} ---\n{content}")
                                extracted_sources[len(extracted_sources) + 1] = found_urls[i]

                        result += "\n\n[AUTOMATIC DEPTH-READ]\n" + "".join(chained_data)

                tool_triggered = True
                current_step.update({"tool": tool_name, "query": args_str, "result_summary": str(result)[:200]})

            except Exception as e:
                app_logger.exception(f"Tool {tool_name} failed")
                tool_context = f"[ERROR] Tool {tool_name} crashed: {e}"
                tool_triggered = True

        if not tool_triggered:
            break

        # 5. Construct Directing Context
        if tool_context:
            final_context = tool_context
        else:
            directive = "Analyze this result and decide: do you need more tools or can you answer the user?"
            final_context = f"[RESULT {tool_name}]\n{result}\n\n{directive}"

        execution_steps.append(current_step)

        # 6. Feed back to LLM
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": final_context})

        try:
            response, usage = await asyncio.wait_for(brain.chat(messages), timeout=120)
            brain.record_usage(usage)
            context_mgr.token_count = usage.get("prompt_tokens", 0)
            response = response.replace("<thought>", "").replace("</thought>", "").strip()
        except Exception as e:
            app_logger.exception(f"Inference failed in tool loop")
            response += f"\n\n[Critical Error: {e}]"
            break

        tool_step += 1

    return response, execution_steps, extracted_sources, usage
