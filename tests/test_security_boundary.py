"""Adversarial policy identity tests; no foreign tool is executed."""
import unittest
from salesforce_guard.policy import decision,TOOLS
from salesforce_guard.access_capture import query_plan


class BoundaryTests(unittest.TestCase):
    def test_schema_discovery_is_scoped_and_execution_bridge_stays_blocked(self):
        for names in ('sfg_compare_demo', ['sfg_access'], sorted(TOOLS)):
            self.assertIsNone(decision('tool_describe', {'names': names}))
        for args in (None, {}, {'names': []}, {'names': ['terminal']},
                     {'names': ['sfg_access', 'mcp__salesforce__query']},
                     {'names': ['sfg_access ']}, {'names': [None]},
                     {'names': ['sfg_access'] * 10}, {'names': {'sfg_access': True}}):
            self.assertEqual(decision('tool_describe', args)['action'], 'block', repr(args))
        self.assertEqual(decision('tool_call', {'name': 'sfg_access', 'arguments': {}})['action'], 'block')

    def test_tool_identity_lookalikes_cannot_bypass_exact_allowlist(self):
        for tool in TOOLS:
            for name in (tool+' ', ' '+tool,tool.upper(),tool+'\x00',tool+';terminal',tool+'.terminal',tool+'\nterminal'):
                self.assertEqual(decision(name)['action'],'block',repr(name))
        for name in ('sfg_аccess','sfg＿scan','terminal','mcp__salesforce__deploy','browser','python','send_message',None,{},[]):
            self.assertEqual(decision(name)['action'],'block',repr(name))

    def test_query_shape_rejects_common_injection_payloads(self):
        for value in ("Account' OR Name != ''",'Account; DROP','Account\nLIMIT 1','Account/*x*/','Account--','Account\x00','Account.*','(SELECT Id FROM User)','Ａccount','Account%27'):
            with self.assertRaises(ValueError):query_plan('entity',name=value)


if __name__=='__main__':unittest.main()
