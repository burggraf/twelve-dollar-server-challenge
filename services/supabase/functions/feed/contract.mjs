export class HttpError extends Error {
 constructor(status,message){super(message);this.status=status;}
}
export function positiveId(raw) {
 if(typeof raw!=='string'||!/^\d+$/.test(raw))throw new HttpError(400,'invalid post id');
 const value=BigInt(raw);
 if(value<=0n||value>9223372036854775807n)throw new HttpError(400,'invalid post id');
 return value.toString();
}
export function validateBody(value) {
 if(typeof value?.body!=='string'||!value.body.trim())throw new HttpError(400,'body is required');
 const body=value.body.trim();
 if(Array.from(body).length>500)throw new HttpError(400,'body must be at most 500 characters');
 return body;
}
// Match scalar-valid JSON decoding, never replace invalid Unicode silently.
export function parseJSON(bytes) {
 const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 function valid(item,depth=0){
  if(depth>128)throw new SyntaxError('JSON nesting limit');
  if(typeof item==='string')return item.isWellFormed();
  if(typeof item==='number')return Number.isFinite(item);
  if(item&&typeof item==='object')return Object.entries(item).every(([k,v])=>k.isWellFormed()&&valid(v,depth+1));
  return true;
 }
 if(!valid(value))throw new SyntaxError('Invalid JSON scalar');
 return value;
}
const encoder=new TextEncoder();
function decode(raw) {
 if(!/^[A-Za-z0-9_-]*$/.test(raw))throw new Error('base64url');
 return Uint8Array.from(atob(raw.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
}
function encode(bytes) {return btoa(String.fromCharCode(...bytes)).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');}
const jsonPart=raw=>parseJSON(decode(raw));
const key=(secret,usage)=>crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,[usage]);
export async function authenticate(header,secret,now=Date.now()/1000) {
 if(!header?.startsWith('Bearer '))throw new HttpError(401,'missing bearer token');
 let payload;
 try {
  const parts=header.slice(7).split('.');
  if(parts.length!==3||jsonPart(parts[0])?.alg!=='HS256')throw new Error('JWT');
  if(!await crypto.subtle.verify('HMAC',await key(secret,'verify'),decode(parts[2]),encoder.encode(parts[0]+'.'+parts[1])))throw new Error('signature');
  payload=jsonPart(parts[1]);
  if(typeof payload?.exp!=='number'||!Number.isFinite(payload.exp)||now>=payload.exp)throw new Error('expiry');
  if('nbf' in payload&&(typeof payload.nbf!=='number'||!Number.isFinite(payload.nbf)||now<payload.nbf))throw new Error('nbf');
 } catch {throw new HttpError(401,'invalid or expired token');}
 try {
  if(typeof payload.sub!=='string'||typeof payload.username!=='string')throw new Error('claims');
  return {id:positiveId(payload.sub),username:payload.username};
 } catch {throw new HttpError(401,'invalid token payload');}
}
export async function bridgeToken(identity,secret,now=Math.floor(Date.now()/1000)) {
 const claims={role:'feed_writer',app_user_id:identity.id,exp:now+60};
 const text=[{alg:'HS256',typ:'JWT'},claims].map(v=>encode(encoder.encode(JSON.stringify(v)))).join('.');
 return text+'.'+encode(new Uint8Array(await crypto.subtle.sign('HMAC',await key(secret,'sign'),encoder.encode(text))));
}
