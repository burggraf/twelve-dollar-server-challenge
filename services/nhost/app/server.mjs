import {createServer} from 'node:http';
import {HttpError,positiveId,validateBody,authenticate,parseJSON} from '/shared/contract.mjs';
import {nativeToken,integerJSON} from './native-contract.mjs';

const {GRAPHQL_URL,COMPAT_JWT_SECRET,NATIVE_JWT_SECRET}=process.env;
if(!GRAPHQL_URL||!COMPAT_JWT_SECRET||!NATIVE_JWT_SECRET)throw new Error('Required private runtime inputs missing');
const started=performance.now();
const decoder=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true});

async function rpc(name,args,identity) {
 const field='nhost_'+name;
 const declaration=args===undefined?'':'($args:'+field+'_args!)';
 const argumentsText=args===undefined?'':'(args:$args)';
 const query=(identity?'mutation':'query')+declaration+'{'+field+argumentsText+'{payload}}';
 const headers={'content-type':'application/json'};
 if(identity)headers.authorization='Bearer '+nativeToken(identity,NATIVE_JWT_SECRET);
 const response=await fetch(GRAPHQL_URL,{method:'POST',headers,body:JSON.stringify({query,variables:args===undefined?{}:{args}}),signal:AbortSignal.timeout(10000)});
 if(!response.ok){await response.body?.cancel();throw new Error('Native API failed');}
 const value=parseJSON(await response.arrayBuffer());
 if(value.errors||!Array.isArray(value.data?.[field])||value.data[field].length!==1)throw new Error('Native API result shape');
 return value.data[field][0].payload;
}
function post(row) {
 if(!row||typeof row.author!=='string'||typeof row.created_at!=='string'||typeof row.body_b64!=='string')throw new Error('Native post shape');
 const bytes=Uint8Array.from(atob(row.body_b64),character=>character.charCodeAt(0));
 return {id:integerJSON(row.id,1),body:decoder.decode(bytes),created_at:row.created_at,author:row.author,like_count:integerJSON(row.like_count,0)};
}
async function route(req) {
 const path=new URL(req.url,'http://localhost').pathname;
 if(req.method==='GET'&&path==='/health') {
  try {
   if(await rpc('health')!==true)throw new Error('Storage probe failed');
   return [200,{status:'ok',db:'ok',uptime_s:Math.max(0,Math.floor((performance.now()-started)/1000))}];
  } catch {return [503,{status:'degraded',db:'unreachable',error:'storage probe failed'}];}
 }
 if(req.method==='GET'&&path==='/feed') {
  const rows=await rpc('feed');
  if(!Array.isArray(rows)||rows.length>20)throw new Error('Native feed shape');
  return [200,{posts:rows.map(post)}];
 }
 const detail=/^\/posts\/([^/]+)$/.exec(path);
 if(req.method==='GET'&&detail) {
  const row=await rpc('detail',{p_post_id:positiveId(detail[1])});
  if(row===null)throw new HttpError(404,'post not found');
  return [200,{post:post(row)}];
 }
 const like=/^\/posts\/([^/]+)\/like$/.exec(path);
 if(req.method==='POST'&&(path==='/posts'||like)) {
  const identity=await authenticate(req.headers.authorization,COMPAT_JWT_SECRET);
  if(like) {
   const result=await rpc('like_post',{p_post_id:positiveId(like[1])},identity);
   if(result===null)throw new HttpError(404,'post not found');
   if(typeof result.liked!=='boolean'||result.liked!==true||typeof result.already_liked!=='boolean')throw new Error('Native like shape');
   return [result.already_liked?200:201,{liked:true,already_liked:result.already_liked,post_id:integerJSON(result.post_id,1)}];
  }
  let value;
  try {const chunks=[];for await(const chunk of req)chunks.push(chunk);value=parseJSON(Buffer.concat(chunks));}
  catch {throw new HttpError(400,'malformed JSON body');}
  const body=validateBody(value);
  const created=post(await rpc('create_post',{p_body_b64:Buffer.from(body).toString('base64')},identity));
  created.author=identity.username;
  return [201,{post:created}];
 }
 throw new HttpError(404,'not found');
}
function send(res,status,value) {
 if(res.destroyed)return;
 const body=JSON.stringify(value);
 res.writeHead(status,{'content-type':'application/json'});res.end(body);
}
const server=createServer(async(req,res)=>{
 try {const [status,value]=await route(req);send(res,status,value);}
 catch(error) {send(res,error instanceof HttpError?error.status:500,{error:error instanceof HttpError?error.message:'internal server error'});}
 finally {req.resume();}
});
server.listen(4000,'0.0.0.0',()=>console.log('NHOST_HTTP_LISTENING'));
let closing=false;
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>{
 if(closing)return;closing=true;server.close(()=>process.exit(0));
});
