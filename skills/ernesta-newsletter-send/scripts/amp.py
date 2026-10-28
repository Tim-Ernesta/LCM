import re,json
class Amp:
    def __init__(s,data,email,attrs=None):
        s.data=data; s.vars={'emailaddr':email}; s.attrs=attrs or {}
    TOK=re.compile(r'\s*(?:(?P<str>"(?:[^"]*)")|(?P<var>@[A-Za-z_][A-Za-z0-9_]*)|(?P<num>-?\d+(?:\.\d+)?)|(?P<op>==|!=|>=|<=|>|<)|(?P<id>[A-Za-z_][A-Za-z0-9_]*)|(?P<p>[(),]))')
    def tokens(s,x):
        out=[];i=0
        while i<len(x):
            m=s.TOK.match(x,i)
            if not m:
                if x[i:].strip()=='' : break
                raise ValueError('tok '+x[i:i+30])
            i=m.end(); k=m.lastgroup; out.append((k,m.group(k)))
        return out
    def ev(s,x):
        s.t=s.tokens(x); s.i=0; v=s.cmp(); return v
    def peek(s): return s.t[s.i] if s.i<len(s.t) else (None,None)
    def nxt(s): v=s.t[s.i]; s.i+=1; return v
    def cmp(s):
        a=s.unary()
        k,v=s.peek()
        if k=='op':
            s.nxt(); b=s.unary()
            if isinstance(a,str) and isinstance(b,str): a,b=a.lower(),b.lower()
            if v=='==': return a==b
            if v=='!=': return a!=b
            a,b=(a or 0),(b or 0)
            return {'>':lambda:a>b,'<':lambda:a<b,'>=':lambda:a>=b,'<=':lambda:a<=b}[v]()
        return a
    def unary(s):
        k,v=s.peek()
        if k=='id' and v.upper()=='NOT': s.nxt(); return not s.unary()
        return s.prim()
    def prim(s):
        k,v=s.nxt()
        if k=='str': return v[1:-1]
        if k=='num': return float(v) if '.' in v else int(v)
        if k=='var': return s.vars.get(v[1:],'')
        if k=='id':
            if s.peek()[1]=='(':
                s.nxt(); args=[]
                if s.peek()[1]!=')':
                    while True:
                        args.append(s.cmp())
                        if s.peek()[1]==',': s.nxt(); continue
                        break
                assert s.nxt()[1]==')'
                return s.fn(v,args)
            if v.lower()=='emailaddr': return s.vars['emailaddr']
            return v
        raise ValueError(k)
    def fn(s,n,a):
        n=n.lower()
        if n=='v': return a[0]
        if n=='empty': return a[0] in ('',None) or a[0]==[]
        if n=='rowcount': return len(a[0])
        if n=='row': return a[0][a[1]-1]
        if n=='field':
            r=a[0]; k=a[1].lower(); return r.get(k,'') if isinstance(r,dict) else ''
        if n=='lookuprows':
            de=a[0]; crit=[(a[i].lower(),a[i+1]) for i in range(1,len(a),2)]
            return [r for r in s.data.get(de,[]) if all(str(r.get(k,'')).lower()==str(v).lower() for k,v in crit)]
        if n=='attributevalue': return s.attrs.get(a[0],'')
        if n=='redirectto': return a[0]
        if n=='trim': return str(a[0]).strip()
        if n=='concat': return ''.join(str(x) for x in a)
        if n=='uppercase': return str(a[0]).upper()
        if n=='indexof': return str(a[0]).find(a[1])+1
        if n=='subtract': return a[0]-a[1]
        if n=='substring': return str(a[0])[a[1]-1:a[1]-1+a[2]]
        raise ValueError('fn '+n)
    def run_block(s,code,stack):
        code=re.sub(r'/\*.*?\*/','',code,flags=re.S)
        for line in [l.strip() for l in code.splitlines() if l.strip()]:
            u=line.upper()
            if u.startswith('IF ') and u.endswith(' THEN'):
                c=bool(s.ev(line[3:-5])) if all(stack) else False
                stack.append(c); stack_taken.append(c)
            elif u.startswith('ELSEIF ') and u.endswith(' THEN'):
                if stack_taken[-1] or not all(stack[:-1]): stack[-1]=False
                else:
                    c=bool(s.ev(line[7:-5])); stack[-1]=c; stack_taken[-1]=c
            elif u=='ELSE':
                stack[-1]=(not stack_taken[-1]) and all(stack[:-1]); stack_taken[-1]=stack_taken[-1] or stack[-1]
            elif u=='ENDIF': stack.pop(); stack_taken.pop()
            elif u.startswith('SET '):
                if all(stack):
                    m=re.match(r'SET\s+@(\w+)\s*=\s*(.*)$',line,re.I|re.S); s.vars[m.group(1)]=s.ev(m.group(2))
            else: raise ValueError('stmt '+line[:60])
    def render(s,tpl):
        global stack_taken
        stack_taken=[]; stack=[]
        out=[]; pos=0
        pat=re.compile(r'%%\[(.*?)\]%%|%%=(.*?)=%%',re.S)
        for m in pat.finditer(tpl):
            if all(stack): out.append(tpl[pos:m.start()])
            pos=m.end()
            if m.group(1) is not None: s.run_block(m.group(1),stack)
            elif all(stack): out.append(str(s.ev(m.group(2))))
        if all(stack): out.append(tpl[pos:])
        assert not stack,'unbalanced'
        return ''.join(out)
