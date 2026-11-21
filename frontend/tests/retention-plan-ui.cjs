// Run with a local Vite server and Playwright available through NODE_PATH.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
async function run() {
  const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL || 'msedge'});
  try {
    const page=await browser.newPage({viewport:{width:1280,height:1000}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    let state={plan_id:1,plan_status:'DRAFT',version:0,start_date:'2026-10-01',end_date:'2026-12-31',detail:null,
      employment_options:[{job_placement_id:1,employment_start_date:'2026-03-31',employer_name:'検証企業',industry:'事務',employer_address:'検証所在地',employer_phone:null,employer_contact_person:null,employment_type:'正規'}],
      related_support_organizations:[],organization_options:[],goals:[],goal_assessments:[],assessor_types:[],
      permissions:{edit:true,create:true,delete:true,evaluate:false,view_pii:false,edit_pii:false}};
    await page.route('**/api/plans/1/**',async route=>{
      const request=route.request();const url=new URL(request.url());
      if(request.method()!=='GET') {
        const data=request.postDataJSON();assert.equal(data.version,state.version);
        if(url.pathname.endsWith('/retention-detail')) {
          assert.equal(data.health_status_notes,undefined);
          state.detail={...state.detail,...data,support_items:state.detail?.support_items || []};
        } else if(url.pathname.endsWith('/retention-support-items')) {
          state.detail.support_items.push({id:state.detail.support_items.length+1,sequence_no:state.detail.support_items.length+1,
            ...data,implementation_status:null,achievement_status:null,effect_satisfaction_notes:null,remaining_issues_and_actions:null});
        } else if(url.pathname.endsWith('/retention-evaluation')) {
          state.detail={...state.detail,...data,support_items:data.items.map((item,index)=>({...state.detail.support_items[index],...item}))};
        }
        state.version++;
      }
      await route.fulfill({json:state});
    });
    await page.goto('http://127.0.0.1:5177/tests/retention-plan.html');
    await page.getByLabel('就職記録（承認前に必須）').selectOption('1');
    await page.getByRole('button',{name:'計画詳細を保存',exact:true}).click();
    await page.getByRole('status').filter({hasText:'保存しました'}).waitFor();
    await page.getByRole('button',{name:'職場・労働条件',exact:true}).click();
    await page.getByLabel('業務内容（承認前に必須）').fill('書類整理');
    await page.getByRole('button',{name:'計画詳細を保存',exact:true}).click();
    await page.getByRole('status').filter({hasText:'保存しました'}).waitFor();
    await page.getByRole('button',{name:'本人・生活情報',exact:true}).click();
    await page.getByText('健康状態・支援上の留意事項：閲覧権限が必要です。').waitFor();
    await page.getByLabel('利用目標・本人ニーズ（承認前に必須）').fill('働き続けたい');
    await page.getByRole('button',{name:'計画詳細を保存',exact:true}).click();
    await page.getByRole('status').filter({hasText:'保存しました'}).waitFor();
    await page.getByRole('button',{name:'支援内容',exact:true}).click();
    for(let i=0;i<4;i++) {
      await page.getByLabel(/^支援方針・内容/).fill(`面談${i+1}`);
      await page.getByLabel('頻度',{exact:true}).last().fill('月1回');
      await page.getByRole('button',{name:'支援項目を追加',exact:true}).click();
      await page.waitForFunction(count=>document.querySelectorAll('fieldset').length===count, i+2);
    }
    assert.equal(state.detail.support_items.length,4);
    state.plan_status='ACTIVE';state.permissions={...state.permissions,edit:false,create:false,delete:false,evaluate:true};
    await page.reload();
    await page.getByRole('button',{name:'評価',exact:true}).click();
    assert.equal(await page.getByLabel('実施状況').first().inputValue(),'');
    await page.getByLabel('評価日',{exact:true}).fill('2026-10-02');
    await page.getByLabel('実施状況').first().selectOption('DONE');
    await page.getByLabel('総括評価',{exact:true}).fill('継続支援');
    await page.getByRole('button',{name:'評価を記録',exact:true}).click();
    await page.getByRole('status').filter({hasText:'保存しました'}).waitFor();
    assert.equal(state.detail.support_items[0].implementation_status,'DONE');
    assert.deepEqual(errors,[]);
    if(process.env.UI_SCREENSHOT_PATH) await page.screenshot({path:process.env.UI_SCREENSHOT_PATH,fullPage:true});
    console.log('PASS: detail editing, private masking, four support items, NULL evaluation and ACTIVE evaluation');
  } finally {await browser.close();}
}
run().catch(error=>{console.error(error);process.exitCode=1;});
