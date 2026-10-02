#!/usr/bin/env python3
"""Produce a bounded unweaving-policy certificate from a case or example packet."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import engine,producer

def integer(value: str) -> int:
    try: return int(value,0)
    except ValueError as exc: raise argparse.ArgumentTypeError('expected an integer mask') from exc

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--on',required=True,type=integer)
    parser.add_argument('--off',required=True,type=integer)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.input.stat().st_size>16*1024*1024:raise ValueError('input exceeds 16 MiB')
        raw=json.loads(args.input.read_text())
        if type(raw) is dict and 'case' in raw:raw=raw['case']
        case=engine.parse_case(raw)
        certificate=producer.solve(case,args.on,args.off)
        # Exclusive creation avoids destroying a previously produced witness.
        with args.output.open('x') as output:
            json.dump({'case':raw,'certificate':certificate},output,indent=2);output.write('\n')
    except (ValueError,TypeError,KeyError,OSError,RecursionError) as exc:
        print(str(exc),file=sys.stderr);return 2
    print(json.dumps({'produced':certificate['kind'],'verification_required':True}))
    return 0
if __name__=='__main__':raise SystemExit(main())
