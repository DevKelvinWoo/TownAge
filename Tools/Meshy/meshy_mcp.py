"""Call the pinned official Meshy MCP; keep responses and task IDs locally.

Use the existing Python environment with the MCP SDK installed. This helper
does not retry create calls or automatically submit a paid generation.
"""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
SAFE = {'meshy_check_balance', 'meshy_get_task_status', 'meshy_list_tasks',
        'meshy_list_models', 'meshy_list_animations', 'meshy_list_usage',
        'meshy_download_model'}

async def run(args):
    request = None
    if args.action == 'call':
        if not args.request:
            raise ValueError('call requires --request JSON containing tool and arguments')
        request = json.loads(Path(args.request).read_text(encoding='utf-8-sig'))
        name = request['tool']
        if name == 'meshy_cancel_task':
            raise ValueError('Task deletion is deliberately excluded from this pipeline helper')
        if name not in SAFE and not args.allow_create:
            raise ValueError('A potentially paid call requires explicit --allow-create')
    filename = (datetime.now(timezone.utc).strftime('call-%Y%m%dT%H%M%S%fZ')
                if args.action == 'call' else args.action)
    output = Path(args.output) if args.output else ROOT / 'Saved/Meshy' / (filename + '.json')
    if args.action == 'call' and output.exists():
        raise ValueError('Choose a new response filename; existing task receipts must be retained')
    output.parent.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command='powershell.exe', args=[
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(ROOT / 'Tools/Meshy/launch_meshy_mcp.ps1')], cwd=str(ROOT))
    async with stdio_client(params) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            initialized = await session.initialize()
            catalog = await session.list_tools()
            names = {tool.name for tool in catalog.tools}
            if args.action == 'list-tools':
                output.write_text(catalog.model_dump_json(indent=2), encoding='utf-8')
                print(json.dumps({'server': initialized.serverInfo.model_dump(),
                                  'tools': sorted(names), 'schema_file': str(output)}))
                return
            name = 'meshy_check_balance' if args.action == 'check' else request['tool']
            arguments = {} if args.action == 'check' else request.get('arguments', {})
            if name == 'meshy_get_task_status':
                arguments.setdefault('wait', False)
                if arguments['wait']:
                    arguments['timeout_seconds'] = min(arguments.get('timeout_seconds', 45), 45)
            if name not in names:
                raise ValueError('Requested tool is absent from the live server catalog')
            # Record intent BEFORE any paid call, so an interrupted request is
            # reconciled against task history instead of blindly sent again.
            journal = ROOT / 'Saved/Meshy/calls.jsonl'
            journal.parent.mkdir(parents=True, exist_ok=True)
            with journal.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(),
                                         'tool': name, 'response_file': str(output),
                                         'state': 'submitted_no_automatic_retry'}) + '\n')
            result = await session.call_tool(name, arguments)
            output.write_text(result.model_dump_json(indent=2), encoding='utf-8')
            print(json.dumps({'tool': name, 'is_error': bool(result.isError),
                              'response_file': str(output)}))
            if result.isError:
                raise RuntimeError('Meshy returned an error; inspect the local response before retrying')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list-tools', 'check', 'call'])
    parser.add_argument('--request')
    parser.add_argument('--output')
    parser.add_argument('--allow-create', action='store_true')
    args = parser.parse_args()
    asyncio.run(run(args))

if __name__ == '__main__':
    main()
