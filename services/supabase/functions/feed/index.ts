import {HttpError,positiveId,validateBody,authenticate,bridgeToken,parseJSON} from './contract.mjs';
const compatSecret=Deno.env.get('COMPAT_JWT_SECRET')!;
const nativeSecret=Deno.env.get('NATIVE_JWT_SECRET')!;
const anonKey=Deno.env.get('SUPABASE_ANON_KEY')!;
const rest=Deno.env.get('REST_URL')!;
const started=Number(Deno.env.get('SERVING_STARTED_AT')||Date.now());
const encoder=new TextEncoder();
const decoder=new TextDecoder('utf-8',{fatal:true});
function json(status:number,value:unknown){return new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json'}});}
function post(row:any){
 if(!row||!Number.isSafeInteger(row.id)||!Number.isSafeInteger(row.like_count)||typeof row.author!=='string'||typeof row.created_at!=='string'||typeof row.body_b64!=='string')throw new Error('RPC shape');
 const body=decoder.decode(Uint8Array.from(atob(row.body_b64),c=>c.charCodeAt(0)));
 // Reconstruct original property order; native JSONB key ordering is not the contract.
 return {id:row.id,body,created_at:row.created_at,author:row.author,like_count:row.like_count};
}
async function rpc(name:string,args:unknown={},identity?:{id:string,username:string}){
 const headers:Record<string,string>={'content-type':'application/json','apikey':anonKey};
 if(identity)headers.authorization='Bearer '+await bridgeToken(identity,nativeSecret);
 const response=await fetch(rest+'/rpc/'+name,{method:'POST',headers,body:JSON.stringify(args)});
 if(!response.ok){await response.body?.cancel();throw new Error('RPC failed');}
 const text=await response.text();return text?JSON.parse(text):null;
}
Deno.serve(async(req:Request)=>{
 const path=new URL(req.url).pathname;
 try {
  if(req.method==='GET'&&path==='/health'){
   try {
    if(await rpc('health')!==true)throw new Error('storage probe');
    return json(200,{status:'ok',db:'ok',uptime_s:Math.max(0,Math.floor((Date.now()-started)/1000))});
   } catch {return json(503,{status:'degraded',db:'unreachable',error:'storage probe failed'});}
  }
  if(req.method==='GET'&&path==='/feed')return json(200,{posts:(await rpc('feed')).map(post)});
  const detail=/^\/posts\/([^/]+)$/.exec(path);
  if(req.method==='GET'&&detail){
   const result=await rpc('detail',{p_post_id:positiveId(detail[1])});
   if(!result)throw new HttpError(404,'post not found');return json(200,{post:post(result)});
  }
  const like=/^\/posts\/([^/]+)\/like$/.exec(path);
  if(req.method==='POST'&&(path==='/posts'||like)){
   const identity=await authenticate(req.headers.get('authorization'),compatSecret);
   if(like){
    const result=await rpc('like_post',{p_post_id:positiveId(like[1])},identity);
    if(!result)throw new HttpError(404,'post not found');
    return json(result.already_liked?200:201,{liked:result.liked,already_liked:result.already_liked,post_id:result.post_id});
   }
   let value;try {value=parseJSON(await req.arrayBuffer());}catch{throw new HttpError(400,'malformed JSON body');}
   const body=validateBody(value);
   const p_body_b64=btoa(String.fromCharCode(...encoder.encode(body)));
   const created=post(await rpc('create_post',{p_body_b64},identity));
   // Same signed-claim response semantics as the compatibility contract.
   created.author=identity.username;
   return json(201,{post:created});
  }
  throw new HttpError(404,'not found');
 } catch(error){return error instanceof HttpError?json(error.status,{error:error.message}):json(500,{error:'internal server error'});}
});
