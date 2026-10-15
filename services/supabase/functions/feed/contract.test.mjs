import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { positiveId, validateBody, authenticate, bridgeToken, parseJSON } from './contract.mjs';
const secret='unit-test-only-compatibility-key-not-a-deployment-secret';
const native='unit-test-only-native-key-not-a-deployment-secret';
function sign(payload,header={alg:'HS256',typ:'JWT'}) {
 const text=[header,payload].map(v=>Buffer.from(JSON.stringify(v)).toString('base64url')).join('.');
 return text+'.'+createHmac('sha256',secret).update(text).digest('base64url');
}
test('JSON rejects invalid UTF-8, unpaired surrogates and non-finite numbers without lossy replacement',()=>{
 const encoder=new TextEncoder();
 assert.deepEqual(parseJSON(encoder.encode('{"body":"café 😀"}')),{body:'café 😀'});
 for(const raw of [String.raw`{"body":"\ud800"}`,String.raw`{"extra":{"\udfff":"ignored"},"body":"ok"}`,'{"body":"ok","extra":1e999}'])assert.throws(()=>parseJSON(encoder.encode(raw)));
 assert.throws(()=>parseJSON(Uint8Array.from([123,34,120,34,58,34,255,34,125])));
});
const payload={sub:'001',username:'test-user',exp:200};
const isError=(status,message)=>e=>e.status===status && e.message===message;
test('positive IDs preserve exact signed-64-bit identity and canonical decimal form',()=>{
 assert.equal(positiveId('001'),'1');assert.equal(positiveId('9223372036854775807'),'9223372036854775807');
 for(const id of ['','0','-1','+1','1.1','1e0',' 1','١','9223372036854775808'])assert.throws(()=>positiveId(id),isError(400,'invalid post id'));
});
test('body uses ECMAScript trim and a 500 Unicode-code-point limit',()=>{
 const text='😀'.repeat(500);assert.equal(validateBody({body:'\ufeff\u00a0'+text+'\u2029'}),text);
 assert.equal(validateBody({body:'\u0085'}),'\u0085');
 assert.throws(()=>validateBody({body:text+'😀'}),isError(400,'body must be at most 500 characters'));
 for(const body of [null,[],5,'text',{}, {body:2},{body:'\ufeff\u00a0'}])assert.throws(()=>validateBody(body),isError(400,'body is required'));
});
test('every write verifies signature, algorithm, numeric expiry/nbf and strict signed payload',async()=>{
 assert.deepEqual(await authenticate('Bearer '+sign(payload),secret,100),{id:'1',username:'test-user'});
 for(const header of [null,'Basic abc','bearer abc'])await assert.rejects(authenticate(header,secret,100),isError(401,'missing bearer token'));
 for(const token of ['abc',sign(payload,{alg:'none'}),sign({...payload,exp:100}),sign({...payload,exp:'future'}),sign({...payload,exp:true}),sign({...payload,nbf:101})])await assert.rejects(authenticate('Bearer '+token,secret,100),isError(401,'invalid or expired token'));
 await assert.rejects(authenticate('Bearer '+sign(payload),'wrong-key',100),isError(401,'invalid or expired token'));
 for(const sub of [0,'0','-1','1.0','1e0',' 1','',null,true])await assert.rejects(authenticate('Bearer '+sign({...payload,sub}),secret,100),isError(401,'invalid token payload'));
 for(const username of [null,5,[],{}])await assert.rejects(authenticate('Bearer '+sign({...payload,username}),secret,100),isError(401,'invalid token payload'));
});
test('native bridge binds only verified subject, never caller role or arbitrary username metadata',async()=>{
 const token=await bridgeToken({id:'2',username:'alice',role:'postgres'},native,100);
 assert.equal(typeof token,'string');
 const [h,p,s]=token.split('.');const claims=JSON.parse(Buffer.from(p,'base64url'));
 assert.deepEqual(claims,{role:'feed_writer',app_user_id:'2',exp:160});
 assert.equal(s,createHmac('sha256',native).update(h+'.'+p).digest('base64url'));
});
