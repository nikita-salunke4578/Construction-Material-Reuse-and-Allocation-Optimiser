const BASE=import.meta.env.VITE_API_URL||'http://localhost:8000/api';
export const getToken=()=>localStorage.getItem('reuse_token');
export async function api(path,opts={}){const headers={...(opts.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(getToken()?{Authorization:`Bearer ${getToken()}`}:{}) ,...opts.headers};const res=await fetch(`${BASE}${path}`,{...opts,headers});if(!res.ok){let msg=`Request failed (${res.status})`;try{msg=(await res.json()).detail||msg}catch{}throw new Error(msg)}if(res.headers.get('content-type')?.includes('text/csv'))return res.blob();return res.json()}
export const login=async(email,password)=>api('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
