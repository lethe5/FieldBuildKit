"""State conflict tests against the production JavaScript controller."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_route_candidate_conflict_and_mapping_roundtrip():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the JavaScript controller unit test')
    controller = Path(__file__).parents[2] / 'qfield_builder/qfield_routes/controller.js'
    script = r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const context=vm.createContext({}); vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
let disk={revision:0,data:{routes:[],active_id:null,settings:{}}};
const clone=x=>JSON.parse(JSON.stringify(x));
const deps={repository:{load:()=>clone(disk),save:(io,base,data,revision)=>{assert.equal(revision,disk.revision);disk={revision:revision+1,data:clone(data)};return clone(disk);}},
 features:()=>[{id:'A',name:'A',coordinate:[127,37],completed:false}],geometry:{coordinate:x=>x},gps:()=>[127,37],uuid:()=> 'route',
 backend:{calculate:async(s,list)=>({stops:list,distance_m:1,duration_s:1,legs:[]})}};
(async()=>{let c=context.create(deps);c.configure({optimizer_url:'https://fixture.invalid'});assert(await c.calculate(false));assert(c.save());
 await c.calculate(true);assert(c.complete('A',true));assert.equal(c.save(),false);assert.equal(c.active().stops[0].completed,true);
 c.state.mapping.completed='done';c.saveSettings();c=context.create(deps);assert.equal(c.state.mapping.completed,'done');
 console.log('candidate conflict and completion mapping restoration passed');
})().catch(e=>{console.error(e);process.exit(1)});
'''
    result = subprocess.run([node, '-e', script, str(controller)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
