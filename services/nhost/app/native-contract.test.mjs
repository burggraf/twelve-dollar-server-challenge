import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import {nativeToken,integerJSON} from './native-contract.mjs';

const key='unit-public-signing-key-NOT-A-REAL-CREDENTIAL';
test('native JWT carries only the verified actor and restricted Hasura role',()=>{
 const value=nativeToken({id:'9007199254740993',username:'not a native claim'},key,100);
 assert.equal(typeof value,'string');
 const parts=value.split('.');assert.equal(parts.length,3);
 assert.deepEqual(JSON.parse(Buffer.from(parts[0],'base64url')),{alg:'HS256',typ:'JWT'});
 assert.deepEqual(JSON.parse(Buffer.from(parts[1],'base64url')),{
  exp:160,'https://hasura.io/jwt/claims':{'x-hasura-default-role':'feed_writer','x-hasura-allowed-roles':['feed_writer'],'x-hasura-user-id':'9007199254740993'}
 });
 assert.equal(parts[2],createHmac('sha256',key).update(parts[0]+'.'+parts[1]).digest('base64url'));
});
test('signed64 IDs and counts serialize as exact JSON numbers, never rounded or quoted',()=>{
 assert.equal(JSON.stringify({id:integerJSON('9007199254740993',1),like_count:integerJSON('0',0)}),'{"id":9007199254740993,"like_count":0}');
 assert.equal(JSON.stringify(integerJSON('9223372036854775807',1)),'9223372036854775807');
});
test('invalid native integer payloads fail closed instead of malformed successful JSON',()=>{
 for(const value of ['-1','01','1.0','1e3','Infinity','NaN','9223372036854775808','1,2',1,null])assert.throws(()=>integerJSON(value,0));
 assert.throws(()=>integerJSON('0',1));
});
