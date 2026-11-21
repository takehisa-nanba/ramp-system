import { useEffect, useState } from 'react';
import { UXField, TextAreaWithCounter } from './common/UXFields';
import { UXSelect } from './common/UXSelect';
import { changeRetention, fetchRetentionDetail, type RetentionResponse, type RetentionItem, type Employment } from '../services/retentionPlans';

const groups: { title: string; fields: [string, string][] }[] = [
  {title: '就労情報', fields: [['handover_notes','就職まで利用していた事業所からの引継ぎ事項']]},
  {title: '職場・労働条件', fields: [['physical_work_environment','物理的環境'],['human_work_environment','人的環境'],
    ['job_description','業務内容（承認前に必須）'],['contract_wage','契約上の賃金（単位も記入）'],['holidays','休日'],['daily_work_hours','1日の勤務時間'],['break_time','休憩時間']]},
  {title: '本人・生活情報',fields: [['health_status_notes','健康状態・支援上の留意事項'],['living_environment_notes','生活環境・生活面のサポート体制'],['user_needs','利用目標・本人ニーズ（承認前に必須）'],['special_notes','特記事項']]},
];
const achievement = [{value:'',label:'未評価'},{value:'ACHIEVED',label:'達成'},{value:'PARTIAL',label:'一部'},{value:'NOT_ACHIEVED',label:'未達成'}];
const implementation = [{value:'',label:'未評価'},{value:'DONE',label:'実施'},{value:'PARTIAL',label:'一部'},{value:'NOT_DONE',label:'未実施'}];
const button = 'rounded-lg bg-blue-700 text-white px-4 py-2 disabled:opacity-40';

export default function RetentionPlanEditor({ planId, onDirtyChange }: { planId: number; onDirtyChange?: (dirty: boolean)=>void }) {
  const [data,setData] = useState<RetentionResponse | null>(null);
  const [fields,setFields] = useState<Record<string,string>>({});
  const [placementId,setPlacementId] = useState('');
  const [employment,setEmployment] = useState<Employment | null>(null);
  const [employmentDirty,setEmploymentDirty] = useState(false);
  const [organizationIds,setOrganizationIds] = useState<string[]>([]);
  const [items,setItems] = useState<RetentionItem[]>([]);
  const [goals,setGoals] = useState<Record<string,string>>({});
  const [assessor,setAssessor] = useState('');
  const [section,setSection] = useState(0);
  const [busy,setBusy] = useState(false);
  const [dirty,setDirty] = useState(false);
  const [error,setError] = useState('');
  const [message,setMessage] = useState('');
  const [deleting,setDeleting] = useState<number | null>(null);
  const [deleteReason,setDeleteReason] = useState('');
  const [editingItem,setEditingItem] = useState<number | null>(null);
  function accept(result: RetentionResponse) {
    setData(result); setItems(result.detail?.support_items || []);
    setFields(Object.fromEntries(Object.entries(result.detail || {}).filter(([,v])=>typeof v==='string') as [string,string][]));
    const selected = result.employment_options.find(p=>p.job_placement_id===result.detail?.job_placement_id);
    setPlacementId(selected ? String(selected.job_placement_id) : ''); setEmployment(selected || null);
    setGoals(Object.fromEntries(result.goal_assessments.map(g=>[`${g.goal_type}:${g.goal_id}`,g.achievement_status || ''])));
    setDirty(false);
    setOrganizationIds(result.related_support_organizations.map(link=>String(link.id)));
    setEmploymentDirty(false);
    setEditingItem(null);
  }
  useEffect(()=>{
    let alive=true; setData(null); setError('');
    fetchRetentionDetail(planId).then(r=>{if(alive) accept(r);}).catch(()=>{if(alive) setError('定着支援計画を取得できませんでした。権限と接続を確認してください。');});
    return ()=>{alive=false;};
  },[planId]);
  useEffect(()=>{
    const warn=(event: BeforeUnloadEvent)=>{if(dirty){event.preventDefault();event.returnValue='';}};
    const navigate=(event: MouseEvent)=>{
      const target=event.target instanceof Element ? event.target.closest('a[href]') : null;
      if(dirty && target && !window.confirm('未保存の変更があります。破棄して移動しますか？')) {event.preventDefault();event.stopPropagation();}
    };
    window.addEventListener('beforeunload',warn); document.addEventListener('click',navigate,true);
    return ()=>{window.removeEventListener('beforeunload',warn);document.removeEventListener('click',navigate,true);};
  },[dirty]);
  useEffect(()=>{onDirtyChange?.(dirty);},[dirty,onDirtyChange]);
  useEffect(()=>()=>{onDirtyChange?.(false);},[onDirtyChange]);
  async function save(path: string, payload: object, method: 'put'|'post'|'delete'='put') {
    if(!data) return;
    setBusy(true);setError('');setMessage('');
    try {accept(await changeRetention(planId,path,{...payload,version:data.version},method));setMessage('保存しました。');setDeleting(null);}
    catch(e: unknown) {const err=e as {response?:{data?:{error?:{message?:string}}}};setError(err.response?.data?.error?.message || '保存できませんでした。再読み込みして確認してください。');}
    finally {setBusy(false);}
  }
  const edit = data?.detail ? data.permissions.edit : data?.permissions.create;
  const setField=(key:string,value:string)=>{setFields(f=>({...f,[key]:value}));setDirty(true);};
  const patchItem=(id:number,key:string,value:string|number)=>{setItems(current=>current.map(i=>i.id===id?{...i,[key]:value}:i));setDirty(true);if(section===3) setEditingItem(id);};
  const detailPayload=()=>{
    const payload: Record<string,unknown> = {};
    for(const group of groups) for(const [key] of group.fields) {
      if (['health_status_notes','living_environment_notes'].includes(key) && !data?.permissions.edit_pii) continue;
      payload[key]=fields[key] || null;
    }
    if(placementId) payload.job_placement_id=Number(placementId);
    payload.organization_link_ids=organizationIds.map(Number);
    if(employmentDirty && employment) {
      const {job_placement_id: _id,...source}=employment;
      payload.employment=source;
    }
    return payload;
  };
  return <section className="bg-white border border-slate-200 rounded-3xl p-6 space-y-4">
    <h3 className="text-xl font-bold">就労定着支援計画の詳細</h3>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {message && <p role="status" className="text-green-700">{message}</p>}
    {!data ? <p>読み込み中です。</p> : <>
      <p className="text-sm text-slate-600">計画内容は下書き時に編集できます。承認後は内容を保持し、有効な計画の評価を別に記録します。</p>
      <nav className="flex flex-wrap gap-2" aria-label="定着支援計画の入力区分">
        {[...groups.map(g=>g.title),'支援内容','評価'].map((title,i)=><button type="button" key={title} aria-pressed={section===i}
          className={`px-3 py-2 rounded-lg ${section===i?'bg-blue-700 text-white':'bg-slate-100'}`}
          onClick={()=>{if(!dirty || window.confirm('未保存の変更があります。破棄して切り替えますか？')){accept(data);setSection(i);}}}>{title}</button>)}
      </nav>
      {section<3 && <div className="space-y-4">
        {section===0 && <>
          <UXSelect label="就職記録（承認前に必須）" value={placementId} disabled={!edit || busy}
            options={[{value:'',label:'就職記録を選択'},...data.employment_options.map(p=>({value:String(p.job_placement_id),label:`${p.employer_name} ／ ${p.employment_start_date}`}))]}
            onChange={e=>{setPlacementId(e.target.value);setEmployment(data.employment_options.find(p=>p.job_placement_id===Number(e.target.value))||null);setDirty(true);}} />
          {employment && <div className="grid md:grid-cols-2 gap-3">
            {([['employer_name','雇用事業主'],['industry','業種'],['employer_address','所在地'],['employer_phone','連絡先'],['employer_contact_person','担当者'],['employment_start_date','就職日'],['employment_type','雇用形態（正規／パート・アルバイト／契約・嘱託／派遣など）']] as [keyof Employment,string][]).map(([key,label])=>
              <UXField key={key} label={label} value={String(employment[key]||'')} readOnly={!data.permissions.edit || key==='employment_start_date'} disabled={busy}
                onChange={e=>{setEmployment({...employment,[key]:e.target.value});setEmploymentDirty(true);setDirty(true);}} />)}
            <p className="md:col-span-2 text-sm text-slate-500">就職日は契約開始の根拠として保持します。企業情報は共通の登録内容です。承認済み計画や他の利用者が参照中の場合は変更できません。</p>
          </div>}
        </>}
        {section===2 && <div><UXSelect label="関わっている支援機関（複数選択可）" multiple disabled={!edit || busy}
          value={organizationIds} options={data.organization_options.map(o=>({value:String(o.id),label:o.name}))}
          onChange={e=>{setOrganizationIds(Array.from(e.target.selectedOptions,option=>option.value));setDirty(true);}} />
          {!data.organization_options.length && <p>利用者に登録された関係機関はありません。</p>}
          <p className="text-xs text-slate-500">利用者の関係機関登録から選択します。CtrlキーまたはCommandキーで複数選択できます。</p></div>}
        {groups[section].fields.map(([key,label])=>{
          const privateField=['health_status_notes','living_environment_notes'].includes(key);
          return privateField && !data.permissions.view_pii ? <p key={key}>{label}：閲覧権限が必要です。</p> :
          <TextAreaWithCounter key={key} label={label} value={fields[key]||''} maxLength={10000} disabled={busy}
            readOnly={!edit || (privateField && !data.permissions.edit_pii)} onChange={e=>setField(key,e.target.value)} />;
        })}
        <button className={button} disabled={!edit || busy} onClick={()=>void save('retention-detail',detailPayload())}>計画詳細を保存</button>
      </div>}
      {section===3 && <div className="space-y-5">
        {!data.detail && <p>就職記録と計画詳細を先に保存してください。</p>}
        {items.map(item=><fieldset key={item.id} disabled={busy || (editingItem!==null && editingItem!==item.id)} className="border rounded-xl p-4 space-y-3 disabled:opacity-60">
          <UXField label="表示順" type="number" min={1} value={item.sequence_no} readOnly={!edit} onChange={e=>patchItem(item.id,'sequence_no',Number(e.target.value))} />
          <TextAreaWithCounter label="目標達成に向けた支援方針・内容" value={item.support_policy_content} maxLength={10000} readOnly={!edit} onChange={e=>patchItem(item.id,'support_policy_content',e.target.value)} />
          <div className="grid md:grid-cols-2 gap-3">{(['start_date','end_date'] as const).map(key=><UXField key={key} label={key==='start_date'?'開始日':'終了日'} type="date" value={item[key]} readOnly={!edit} min={data.start_date} max={data.end_date} onChange={e=>patchItem(item.id,key,e.target.value)} />)}</div>
          <UXField label="頻度" value={item.frequency} readOnly={!edit} onChange={e=>patchItem(item.id,'frequency',e.target.value)} />
          <div className="flex gap-3"><button className={button} disabled={!edit || busy} onClick={()=>void save(`retention-support-items/${item.id}`,{sequence_no:item.sequence_no,support_policy_content:item.support_policy_content,start_date:item.start_date,end_date:item.end_date,frequency:item.frequency})}>この支援項目を保存</button>
            <button className="text-red-700" disabled={!data.permissions.delete || busy} onClick={()=>{setDeleting(item.id);setDeleteReason('');}}>削除</button></div>
        </fieldset>)}
        {data.permissions.create && data.detail && <NewItem key={data.version} start={data.start_date} end={data.end_date} busy={busy || (editingItem!==null && editingItem!==-1)} onEdit={()=>{setDirty(true);setEditingItem(-1);}} onSave={payload=>save('retention-support-items',payload,'post')} />}
        {deleting!==null && <div role="dialog" aria-label="支援項目の削除確認" className="border border-red-200 rounded-xl p-4 space-y-3">
          <TextAreaWithCounter label="削除理由（10文字以上）" value={deleteReason} onChange={e=>setDeleteReason(e.target.value)} />
          <button className={button} disabled={busy || deleteReason.trim().length<10} onClick={()=>void save(`retention-support-items/${deleting}`,{reason:deleteReason},'delete')}>理由を記録して削除</button>
          <button className="ml-3" onClick={()=>setDeleting(null)}>キャンセル</button>
        </div>}
      </div>}
      {section===4 && <div className="space-y-4">
        <p className="text-sm">未評価は空欄のまま保持します。未実施・未達成とは区別します。</p>
        <UXField label="評価日" type="date" value={fields.evaluation_date || ''} readOnly={!data.permissions.evaluate} onChange={e=>setField('evaluation_date',e.target.value)} />
        {data.goals.map(goal=><div key={`${goal.goal_type}:${goal.goal_id}`} className="border rounded-xl p-3">
          <p>{goal.goal_type==='LONG'?'長期':'短期'}目標：{goal.description}</p>
          <p className="text-xs">設定日：{goal.start_date || '未入力'} ／ 達成予定日：{goal.end_date || '未入力'}</p>
          <UXSelect label="達成度" options={achievement} disabled={!data.permissions.evaluate} value={goals[`${goal.goal_type}:${goal.goal_id}`]||''}
            onChange={e=>{setGoals({...goals,[`${goal.goal_type}:${goal.goal_id}`]:e.target.value});setDirty(true);}} />
        </div>)}
        <UXSelect label="目標の評価主体" options={[{value:'',label:'支援員（既定）'},...data.assessor_types.map(a=>({value:String(a.id),label:a.name}))]} value={assessor} disabled={!data.permissions.evaluate} onChange={e=>setAssessor(e.target.value)} />
        {items.map(item=><div key={item.id} className="border rounded-xl p-4 space-y-3">
          <h4 className="font-bold">{item.sequence_no}. {item.support_policy_content}</h4>
          <UXSelect label="実施状況" options={implementation} disabled={!data.permissions.evaluate} value={item.implementation_status||''} onChange={e=>patchItem(item.id,'implementation_status',e.target.value)} />
          <UXSelect label="達成状況" options={achievement} disabled={!data.permissions.evaluate} value={item.achievement_status||''} onChange={e=>patchItem(item.id,'achievement_status',e.target.value)} />
          <TextAreaWithCounter label="効果・満足度" value={item.effect_satisfaction_notes||''} readOnly={!data.permissions.evaluate} onChange={e=>patchItem(item.id,'effect_satisfaction_notes',e.target.value)} />
          <TextAreaWithCounter label="残っている課題と対策" value={item.remaining_issues_and_actions||''} readOnly={!data.permissions.evaluate} onChange={e=>patchItem(item.id,'remaining_issues_and_actions',e.target.value)} />
        </div>)}
        <TextAreaWithCounter label="総括評価" value={fields.overall_evaluation||''} readOnly={!data.permissions.evaluate} onChange={e=>setField('overall_evaluation',e.target.value)} />
        <button className={button} disabled={!data.permissions.evaluate || busy} onClick={()=>void save('retention-evaluation',{
          evaluation_date:fields.evaluation_date,overall_evaluation:fields.overall_evaluation||null,assessor_type_id:Number(assessor),
          items:items.map(i=>({id:i.id,implementation_status:i.implementation_status||null,achievement_status:i.achievement_status||null,effect_satisfaction_notes:i.effect_satisfaction_notes||null,remaining_issues_and_actions:i.remaining_issues_and_actions||null})),
          goals:data.goals.map(g=>({goal_type:g.goal_type,goal_id:g.goal_id,achievement_status:goals[`${g.goal_type}:${g.goal_id}`] || null})),
        },'post')}>評価を記録</button>
      </div>}
    </>}
  </section>;
}

function NewItem({start,end,busy,onSave,onEdit}:{start:string;end:string;busy:boolean;onSave:(payload:object)=>Promise<void>;onEdit:()=>void}) {
  const [content,setContent]=useState(''); const [frequency,setFrequency]=useState('');
  const [startDate,setStart]=useState(start); const [endDate,setEnd]=useState(end);
  return <fieldset disabled={busy} onChange={onEdit} className="border border-blue-200 rounded-xl p-4 space-y-3 disabled:opacity-60">
    <h4 className="font-bold">支援項目を追加</h4>
    <TextAreaWithCounter label="支援方針・内容" value={content} maxLength={10000} onChange={e=>setContent(e.target.value)} />
    <UXField label="開始日" type="date" value={startDate} min={start} max={end} onChange={e=>setStart(e.target.value)} />
    <UXField label="終了日" type="date" value={endDate} min={start} max={end} onChange={e=>setEnd(e.target.value)} />
    <UXField label="頻度" value={frequency} onChange={e=>setFrequency(e.target.value)} />
    <button className={button} disabled={busy || !content.trim() || !frequency.trim()} onClick={()=>void onSave({support_policy_content:content,start_date:startDate,end_date:endDate,frequency})}>支援項目を追加</button>
  </fieldset>;
}
