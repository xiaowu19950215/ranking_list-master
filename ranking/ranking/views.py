import hashlib

from django.views.generic import View
from django_redis import get_redis_connection
from django.http import JsonResponse
import jwt
import json

from user.models import UserProfile

def login_check(func):
    '''
     装饰器  做登录状态的校验,在request中添加一个user
    '''
    def wrapper(self,request,*args,**kwargs):
        # 从request里取token,假设username从token中拿,token_key是123456
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            result = {'code': 10086, 'error': 'Please login!'}
            return JsonResponse(result)
        try:
            res = jwt.decode(token,key='123456',algorithms=['HS256',])
            print(res)
        except Exception as e :
            print(e)
            result = {'code':10086,'error':'Please login'}
            return JsonResponse(result)
        except jwt.ExpiredSignatureError:
            #token过期
            result = {'code':10086, 'error':'Please login.'}
            return JsonResponse(result)
        username = res['user']
        print(username,type(username))
        try:
            # 校验用户名是否存在,UserProfile是用户表
            old_user = UserProfile.objects.get(username=username)
        except Exception as e:
            print(e)
            result = {'code':10010,'error':'User is wrong'}
            return JsonResponse(result)
        request.user = username

        return func(self,request,*args,**kwargs)
    return wrapper


class Ranking_list(View):
    
    @login_check
    def post(self,request):
        '''
        提交自己的rank分数，存入redis中
        成功返回200,
        不成功随机5位数
        '''
        user = request.user
        body = request.body
        print(body.decode())
        json_obj = json.loads(body.decode())
        password = json_obj['password']
        m = hashlib.md5()
        m.update(password.encode())
        try:
            UserProfile.objects.get(username=user, password=m.hexdigest())
        except Exception as e:
            result = {'code': 10111, 'error': 'User or password is wrong'}
            return JsonResponse(result)
        try:
            rank = int(json_obj['rank'])
        except Exception as e :
            result = {'code':10098,'error':'Please give me rank'}
            return JsonResponse(result)
        redis_conn = get_redis_connection('Ranking_list')
        print(rank,user)
        redis_conn.zadd('Ranking_list',{user:rank})
        result = {'code':200,'data':'ok'}
        return JsonResponse(result)

    @login_check
    def put(self, request):
        '''
        前端返回数据，更新自己分数，并获取想要的rank区段的信息
        返回200,和查询出来的rank区段，以及自己的排名
        '''
        user = request.user
        start = 0
        stop = 9
        json_obj = json.loads(request.body.decode())
        user_version = ''
        try:
            user_version = json_obj['version']
        except Exception as e:
            print('没有版本信息')
        try:
            scope = json_obj['arange']
            if len(scope) == 2:
                start = int(scope[0])-1
                stop = int(scope[1])-1
        except Exception as e:
            print('默认查询1至10名')
        try:
            rank = int(json_obj['rank'])
        except Exception as e :
            result = {"code":10098,"error":"Please give me rank"}
            return JsonResponse(result)
        redis_conn = get_redis_connection('Ranking_list')
        redis_conn.zadd('Ranking_list',{user:rank})
        user_rank = int(redis_conn.zrevrank('Ranking_list',user)) +1
        me = {}
        me['rank_top'] = user_rank
        me['user'] = user
        me['rank_score'] = rank
        rank_list = ranking_list(start,stop)
        rank_list.append(me)
        result = {"code":200,"data":{"rank_list":rank_list}}
        if user_version != '':
            version = compare_version(user_version)
            result['data']['version'] = version
        return JsonResponse(result)





def ranking_list(start=0,stop=9):
    '''
    从redis中拿想要的区段，默认第1至10名
    '''
    redis_conn = get_redis_connection('Ranking_list')
    rank_ = redis_conn.zrevrange('Ranking_list',start,stop,withscores=True)
    if not rank_:
        return
    rank_list = []
    i = 0
    for rank in rank_:
        user = {}
        i += 1
        user['rank_top'] = i
        # b'' 需要decode()
        user['user'] = rank[0].decode()
        # float 不需要decode()
        user['rank_score'] = rank[1]
        rank_list.append(user)
    return rank_list

def compare_version(version):
    '''
        比较查看客户端版本与服务器版本
    :param version: 客户端的版本号
    :return: 客户端小为-1,客户端大为1(基本不可能),其余为0
    '''
    now_version = '3.00.3.1'
    nv = now_version.split('.')
    ver = version.split('.')
    nv = [int(k) for k in nv]
    ver = [int(c) for c in ver]
    if len(ver) <= len(nv):
        for i in range(len(ver)):
            if ver[i] < nv[i] :
                return -1
            elif ver[i] == nv[i] and i != len(ver)-1:
                continue
            elif ver[i] == nv[i] and i == len(ver)-1 and i == len(nv)-1:
                return 0
            elif i == len(ver)-1 and i != len(nv)-1:
                for k in range(1,len(nv)-i):
                    if nv[-k] != 0:
                        return -1
                return
            else:
                return 1
    else:
        return 1

