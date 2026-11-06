"""A deliberately narrow tool boundary for an isolated Hermes review profile.

No inspection of shell command strings: all foreign executable tools are denied.
This is a host tool gate, not an OS sandbox or an in-org access control.
"""
TOOLS = frozenset({'sfg_scan', 'sfg_demo', 'sfg_report', 'sfg_policy', 'sfg_impact', 'sfg_compare', 'sfg_compare_demo', 'sfg_changes','sfg_access'})
DISCOVERY = frozenset({'tool_search', 'skills_list', 'skill_view'})


def decision(tool_name, args=None):
    if not isinstance(tool_name, str):
        return {'action': 'block', 'message': 'Salesforce Guard: missing tool identity; review profile permits only its review tools.'}
    if tool_name in TOOLS | DISCOVERY:
        return None
    # Newer Hermes clients describe deferred schemas before invoking a tool.
    # Scope this read to our own names: describing a connector can contact it.
    # Never permit tool_call, which is a generic execution bridge.
    if tool_name == 'tool_describe' and isinstance(args, dict):
        names = args.get('names')
        if isinstance(names, str):
            names = [names]
        if (isinstance(names, list) and 0 < len(names) <= len(TOOLS)
                and all(isinstance(name, str) and name in TOOLS for name in names)):
            return None
    return {'action': 'block', 'message': 'Salesforce Guard review profile blocked this tool. Only local review and tool/skill discovery are permitted. No Apex execution, deployment, shell, browser, messaging or external connector calls. An operator must switch to a separate profile outside the agent to do other work.'}


def status():
    return {'mode': 'restricted_review_profile', 'allowed_tools': sorted(TOOLS | DISCOVERY),
        'conditional_tools': {'tool_describe': 'Only nonempty names drawn exclusively from the nine Salesforce Guard tools; foreign and mixed requests are blocked.'},
        'default': 'block_foreign_tools', 'live_salesforce_writes': False,
        'model_can_disable_guard': False, 'boundary': 'Hermes pre_tool_call on profiles loading this plugin',
        'limits': ['Not an OS sandbox; does not stop external programs or other Hermes profiles.',
                   'Host must load and invoke this hook; plugin disable/load failure removes this gate.',
                   'Other trusted plugins and host configuration remain part of the trust boundary.',
                   'Scan and report contents are shared with the active Hermes model when requested.']}
