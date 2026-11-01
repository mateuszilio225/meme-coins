"""Consulta pública de diagnóstico. Não lê chaves, carteiras, config ou banco."""
import datetime as dt
import json
import urllib.error
import urllib.request
from meme_research.data import Sources, NoRedirect

url=Sources.fx_url()
print('Relógio UTC:',dt.datetime.now(dt.timezone.utc).isoformat())
print('URL pública:',url)
try:
    request=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'MoonshotResearch/0.1.1'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=20) as response:
        print('HTTP:',response.status)
        data=json.loads(response.read(2_000_001))
        values=data.get('value',[]) if isinstance(data,dict) else []
        print('Cotações recebidas:',len(values))
        print('Prévia de cotações públicas:',json.dumps(values[-3:],ensure_ascii=False))
except urllib.error.HTTPError as error:
    print('HTTP:',error.code)
    body=error.read(4096).decode('utf-8',errors='replace')
    try:
        payload=json.loads(body)
        detail=payload.get('error',{}).get('message','Sem mensagem estruturada') if isinstance(payload,dict) else 'Resposta inesperada'
        if isinstance(detail,dict): detail=detail.get('value','Sem mensagem')
        print('Mensagem pública do serviço:',json.dumps(detail,ensure_ascii=False))
    except (ValueError,AttributeError):
        print('Resposta não JSON. Verifique se há proxy/firewall; nenhum cabeçalho de autenticação foi exibido.')
    raise SystemExit(1)
except (OSError,ValueError) as error:
    print('Falha de rede ou resposta:',type(error).__name__)
    raise SystemExit(1)
