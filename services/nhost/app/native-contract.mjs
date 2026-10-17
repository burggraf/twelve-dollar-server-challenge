import {createHmac} from 'node:crypto';

export function nativeToken(identity,secret,now=Math.floor(Date.now()/1000)) {
 const claims={exp:now+60,'https://hasura.io/jwt/claims':{
  'x-hasura-default-role':'feed_writer','x-hasura-allowed-roles':['feed_writer'],'x-hasura-user-id':identity.id
 }};
 const text=[{alg:'HS256',typ:'JWT'},claims].map(value=>Buffer.from(JSON.stringify(value)).toString('base64url')).join('.');
 return text+'.'+createHmac('sha256',secret).update(text).digest('base64url');
}
export function integerJSON(raw,minimum) {
 if(typeof raw!=='string'||raw.length>19||!/^(0|[1-9][0-9]*)$/.test(raw))throw new Error('Native integer shape');
 const value=BigInt(raw);
 if(value<BigInt(minimum)||value>9223372036854775807n)throw new Error('Native integer range');
 return JSON.rawJSON(raw);
}
