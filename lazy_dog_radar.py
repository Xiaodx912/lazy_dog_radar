import hoshino
import asyncio
import aiohttp
import re
import os
import json
from sqlitedict import SqliteDict

sv = hoshino.Service('Lazy_Dog_Radar')

def get_path(*paths):
    return os.path.join(os.path.dirname(__file__), *paths)
def init_db(db_dir, db_name='group_data.sqlite'):
    return SqliteDict(get_path(db_dir, db_name),
                      encode=json.dumps,
                      decode=json.loads,
                      autocommit=True)

@sv.on_fullmatch(('Find_Lazy_Dog','查代刀','查懒狗'))
async def send_statics(bot,ev):
    db=init_db('./')
    if str(ev['group_id']) not in list(db.keys()):
        await bot.send(ev,f"未设置api地址")
        return
    api=db[ev['group_id']]['api']
    if 'police_id' in db[ev['group_id']].keys():
        police_id=db[ev['group_id']]['police_id']
    else:
        police_id='2854196306'
    session=aiohttp.ClientSession()
    res=await session.get(api,ssl=False)
    data=json.loads(await res.text())
    await session.close()
    if not res.ok:
        await bot.send(ev,f"Get API fail.\n{res.status}:{res.reason}")
        return
    if data['code']!=0:
        await bot.send(ev,f"API err.\n{data['code']}:{data['message']}")
        return
    mdic={}
    for member in data['members']:
        mdic[member['qqid']]={'nick':member['nickname'],'challenge':0,'behalf':0}
    for challenge in data['challenges']:
        mdic[challenge['qqid']]['challenge']+=1
        if challenge['behalf']==None:
            mdic[challenge['qqid']]['behalf']+=1
        else:
            mdic[challenge['behalf']]['behalf']+=1
    mlist=sorted(list(mdic.values()),key=lambda k: k['behalf'],reverse=True)
    if len(mlist)==0:
        await bot.send(ev,"无出刀记录")
        return
    data_all = []
    for m in mlist:
        msg=f"“{m['nick']}”共上报{m['behalf']}刀"
        data ={
            "type": "node",
            "data": {
                "name": "会战警察",
                "uin": police_id,
                "content": msg
            }
        }
        data_all.append(data)
    await bot.send_group_forward_msg(group_id=ev['group_id'], messages=data_all)


@sv.on_prefix('setapi')
async def set_api(bot,ev):
    url=ev.message.extract_plain_text()
    url=url.strip()
    if not re.match(r'^https?:/{2}\w.+$', url):
        await bot.send(ev,"invalid url")
        return
    db=init_db('./')
    gid=ev['group_id']
    if gid not in list(db.keys()):
        db[ev['group_id']]={}
    data=db[gid]
    data['api']=url
    db[gid]=data
    await bot.send(ev,f"api of {gid} changed.")

@sv.on_prefix('setpol')
async def set_police(bot,ev):
    db=init_db('./')
    data=db[ev['group_id']]
    for msg_group in ev["message"]:
        print(msg_group["type"])
        if msg_group["type"] == "at" :
            data['police_id']=msg_group["data"]["qq"]
            db[ev['group_id']]=data
            await bot.send(ev,"police changed")
            return
    qqid=ev.message.extract_plain_text()
    if re.match(r'^[1-9]\d{4,}$', qqid):
        data['police_id']=qqid
        db[ev['group_id']]=data
        await bot.send(ev,"police changed")
