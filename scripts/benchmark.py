"""Reproducible synthetic comparison measurement; no org access or customer data."""
import argparse
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from salesforce_guard.compare import compare_snapshots


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--components',type=int,default=500)
    parser.add_argument('--output',default='output/benchmark.json')
    args=parser.parse_args()
    if not 10<=args.components<=1000: parser.error('Use 10 to 1000 components')
    with tempfile.TemporaryDirectory(prefix='sfg-benchmark-') as tmp:
        root=Path(tmp);candidate=root/'candidate';baseline=root/'destination'
        for folder in (candidate,baseline):
            folder.mkdir()
            (folder/'sfg-snapshot.json').write_text(json.dumps({'schema':'sfg.snapshot.v1','complete_types':['ApexClass']}))
            for i in range(args.components):
                name=f'FictionalPolicy{i:04d}'
                call=f'FictionalPolicy{i-1:04d}.evaluate();' if i else ''
                changed='Integer revision = 2;' if folder==candidate and i%10==0 else ''
                (folder/(name+'.cls')).write_text(f'public with sharing class {name} {{ public static void evaluate() {{ {call} {changed} }} }}')
                (folder/(name+'.cls-meta.xml')).write_text('<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>67.0</apiVersion><status>Active</status></ApexClass>')
        members=''.join(f'<members>FictionalPolicy{i:04d}</members>' for i in range(args.components))
        scope=root/'package.xml';scope.write_text('<Package xmlns="http://soap.sforce.com/2006/04/metadata"><types>'+members+'<name>ApexClass</name></types><version>67.0</version></Package>')
        tracemalloc.start();start=time.perf_counter()
        report=compare_snapshots(candidate,baseline,scope)
        elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        expected=(args.components+9)//10
        assert report['summary']['modified']==expected,report['summary']
        assert report['summary']['unchanged']==args.components-expected,report['summary']
        result={'python':platform.python_version(),'platform':platform.platform(),'components_per_snapshot':args.components,
            'files_per_snapshot':args.components*2+1,'elapsed_seconds':round(elapsed,3),'peak_python_memory_mib':round(peak/1024**2,2),
            'summary':report['summary'],'before_graph_nodes':len(report['before_impact']['nodes']),
            'after_graph_nodes':len(report['after_impact']['nodes']),
            'limitations':'One local synthetic measurement with Python allocation tracing enabled. Not a live-org load test, runtime security proof, or enterprise scalability guarantee.'}
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
