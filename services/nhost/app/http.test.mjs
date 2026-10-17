// Adapter unit tests only: the fixture GraphQL server is NOT native/runtime proof.
import {test,before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {createHmac} from 'node:crypto';

const compat='unit-compat-NOT-A-REAL-CREDENTIAL',native='unit-native-NOT-A-REAL-CREDENTIAL';
let child,backend,requests=[],result,error=false,rawResponse;
const row={id:'9007199254740993',body_b64:Buffer.from('wide\0🦄').toString('base64'),created_at:'2026-01-01T00:00:00.000Z',author:'database-author',like_count:'0'};
function token(){
 const text=[{alg:'HS256',typ:'JWT'},{sub:'1',username:'signed-author',exp:Math.floor(Date.now()/1000)+3600}].map(v=>Buffer.from(JSON.stringify(v)).toString('base64url')).join('.');
 return text+'.'+createHmac('sha256',compat).update(text).digest('base64url');
}
async function request(path,options={}){
 const response=await fetch('http://127.0.0.1:4000'+path,options);
 return {status:response.status,text:await response.text()};
}
before(async()=>{
 backend=createServer(async(req,res)=>{
  const chunks=[];for await(const chunk of req)chunks.push(chunk);
  const body=JSON.parse(Buffer.concat(chunks));requests.push({headers:req.headers,body});
  const field=/\{(nhost_[a-z_]+)/.exec(body.query)?.[1];
  res.writeHead(200,{'content-type':'application/json'});
  res.end(rawResponse??JSON.stringify(error?{errors:[{message:'private backend diagnostic'}]}:{data:{[field]:[{payload:result}]}}));
 });
 await new Promise(resolve=>backend.listen(8080,'127.0.0.1',resolve));
 child=spawn(process.execPath,[new URL('./server.mjs',import.meta.url).pathname],{env:{...process.env,GRAPHQL_URL:'http://127.0.0.1:8080/v1/graphql',COMPAT_JWT_SECRET:compat,NATIVE_JWT_SECRET:native},stdio:['ignore','pipe','pipe']});
 await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(new Error('Adapter readiness signal missing')),5000);
  child.once('exit',()=>{clearTimeout(timer);reject(new Error('Adapter exited before readiness'));});
  child.stdout.on('data',data=>{if(data.toString().includes('NHOST_HTTP_LISTENING')){clearTimeout(timer);resolve();}});
 });
});
after(async()=>{
 if(child&&child.exitCode===null&&child.signalCode===null){const exit=new Promise(resolve=>child.once('exit',resolve));child.kill('SIGTERM');await exit;}
 if(backend)await new Promise(resolve=>backend.close(resolve));
});
test('health requires a successful storage-backed native result',async()=>{
 result=true;error=false;const response=await request('/health');
 assert.equal(response.status,200);const value=JSON.parse(response.text);
 assert.equal(value.db,'ok');assert.equal(value.status,'ok');assert.equal(typeof value.uptime_s,'number');
 assert.equal(requests.at(-1).body.query.includes('nhost_health'),true);
});
test('feed and detail preserve exact numeric IDs, Unicode and property order',async()=>{
 result=[row];let response=await request('/feed');assert.equal(response.status,200);
 const expected='{"id":9007199254740993,"body":"wide\\u0000🦄","created_at":"2026-01-01T00:00:00.000Z","author":"database-author","like_count":0}';
 assert.equal(response.text,'{"posts":['+expected+']}');
 result=row;response=await request('/posts/9007199254740993');assert.equal(response.status,200);assert.equal(response.text,'{"post":'+expected+'}');
 assert.deepEqual(requests.at(-1).body.variables.args,{p_post_id:'9007199254740993'});
});
test('create verifies compatibility JWT and sends only signed native identity and bytes',async()=>{
 result=row;const response=await request('/posts',{method:'POST',headers:{authorization:'Bearer '+token(),'content-type':'application/json','x-hasura-user-id':'2','x-hasura-admin-secret':'must-not-forward'},body:JSON.stringify({body:'  wide\0🦄  ',user_id:2})});
 assert.equal(response.status,201);assert.equal(JSON.parse(response.text).post.author,'signed-author');
 const sent=requests.at(-1);assert.deepEqual(sent.body.variables.args,{p_body_b64:row.body_b64});
 assert.equal(sent.headers['x-hasura-user-id'],undefined);assert.equal(sent.headers['x-hasura-admin-secret'],undefined);
 const parts=sent.headers.authorization.slice(7).split('.');
 const claims=JSON.parse(Buffer.from(parts[1],'base64url'));
 assert.equal(claims['https://hasura.io/jwt/claims']['x-hasura-user-id'],'1');
 assert.equal(parts[2],createHmac('sha256',native).update(parts[0]+'.'+parts[1]).digest('base64url'));
});
test('authentication and request validation fail before native calls',async()=>{
 const count=requests.length;let response=await request('/posts',{method:'POST',body:'not JSON'});
 assert.equal(response.status,401);assert.equal(response.text,'{"error":"missing bearer token"}');
 response=await request('/posts',{method:'POST',headers:{authorization:'Bearer '+token()},body:'not JSON'});
 assert.equal(response.status,400);assert.equal(response.text,'{"error":"malformed JSON body"}');
 response=await request('/posts',{method:'POST',headers:{authorization:'Bearer '+token()},body:JSON.stringify({body:'😀'.repeat(501)})});
 assert.equal(response.status,400);assert.equal(requests.length,count);
});
test('duplicate likes preserve status and exact response fields',async()=>{
 result={liked:true,already_liked:false,post_id:'9007199254740993'};
 let response=await request('/posts/9007199254740993/like',{method:'POST',headers:{authorization:'Bearer '+token()}});
 assert.equal(response.status,201);assert.equal(response.text,'{"liked":true,"already_liked":false,"post_id":9007199254740993}');
 result={...result,already_liked:true};response=await request('/posts/9007199254740993/like',{method:'POST',headers:{authorization:'Bearer '+token()}});assert.equal(response.status,200);
});
test('missing posts and unknown routes keep distinct error contracts',async()=>{
 result=null;let response=await request('/posts/1');assert.equal(response.status,404);assert.equal(response.text,'{"error":"post not found"}');
 response=await request('/unknown');assert.equal(response.status,404);assert.equal(response.text,'{"error":"not found"}');
});
test('backend errors and malformed native successes fail closed without diagnostics',async()=>{
 error=true;let response=await request('/health');assert.equal(response.status,503);assert.equal(response.text,'{"status":"degraded","db":"unreachable","error":"storage probe failed"}');
 response=await request('/feed');assert.equal(response.status,500);assert.equal(response.text,'{"error":"internal server error"}');
 error=false;result=[{...row,id:9007199254740992}];response=await request('/feed');assert.equal(response.status,500);
});
test('stored body reads preserve a leading BOM exactly',async()=>{
 const stored={...row,body_b64:Buffer.from('\uFEFFx').toString('base64')};
 result=[stored];let response=await request('/feed');assert.equal(response.status,200);assert.equal(JSON.parse(response.text).posts[0].body,'\uFEFFx');
 result=stored;response=await request('/posts/9007199254740993');assert.equal(response.status,200);assert.equal(JSON.parse(response.text).post.body,'\uFEFFx');
});
test('native escaped lone surrogates fail closed instead of successful invalid Unicode',async()=>{
 result=[{...row,author:'\ud800'}];const response=await request('/feed');
 assert.equal(response.status,500);assert.equal(response.text,'{"error":"internal server error"}');
});
test('native invalid UTF-8 fails closed without lossy replacement',async()=>{
 const parts=JSON.stringify({data:{nhost_feed:[{payload:[{...row,author:'invalid-UTF8-marker'}]}]}}).split('invalid-UTF8-marker');
 rawResponse=Buffer.concat([Buffer.from(parts[0]),Buffer.from([0xc3,0x28]),Buffer.from(parts[1])]);
 try {const response=await request('/feed');assert.equal(response.status,500);assert.equal(response.text,'{"error":"internal server error"}');}
 finally {rawResponse=undefined;}
});
test('adapter handles SIGTERM with a completed clean exit',async()=>{
 const stopped=new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal})));
 child.kill('SIGTERM');assert.deepEqual(await stopped,{code:0,signal:null});
});
