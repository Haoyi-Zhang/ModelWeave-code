#!/usr/bin/env python3
"""Check one JSON packet, or stream the delivered gzip JSONL evidence.
No producer code is imported. Exit 0 means checked consistency, not authenticity.
"""
import argparse,gzip,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import checker
MAX_LINE=16*1024*1024

def verify_one(packet):
    if type(packet) is not dict or 'case' not in packet or 'certificate' not in packet:
        raise checker.Rejected('packet needs case and certificate')
    return checker.check(packet['case'],packet['certificate'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inputs',type=Path,nargs='+');a=p.parse_args();n=0
    try:
        for path in a.inputs:
            if path.suffix=='.gz':
                with gzip.open(path,'rb') as f:
                    while True:
                        line=f.readline(MAX_LINE+1)
                        if not line:break
                        if len(line)>MAX_LINE:raise checker.Rejected('JSON line exceeds admission limit')
                        verify_one(json.loads(line));n+=1
            else:
                if path.stat().st_size>MAX_LINE:raise checker.Rejected('packet exceeds admission limit')
                verify_one(json.loads(path.read_text()));n+=1
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as ex:
        print(json.dumps({'accepted':False,'checked_before_rejection':n,'error':str(ex)}));return 2
    print(json.dumps({'accepted':True,'packets':n,'meaning':'bounded internal consistency, not general mechanization or authenticity'}));return 0
if __name__=='__main__':raise SystemExit(main())
