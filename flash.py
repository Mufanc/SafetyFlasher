import sys
import json
import requests
from loguru import logger
from random import randint
from time import time, sleep

logger.remove()
logger.add(sys.stdout, format='<level>[*] {message}</level>')


def timestamp():
    return f'{int(time())}'


class WeibanClient(object):
    def __init__(self, userinfo):
        self.userinfo = userinfo
        self.session = requests.session()
        self.current_request = None
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/93.0.4544.0 Safari/537.36'
        })

    def post(self, url, data={}):
        return self.session.post(url, params={'timestamp': timestamp()}, data={
            **self.userinfo,
            **data
        }).json()

    def flash(self):
        tasks = self.post('https://weiban.mycourse.cn/pharos/index/listStudyTask.do')['data']
        logger.debug('发现课程列表：')
        for i, task in enumerate(tasks):
            logger.info(f'{i+1: >2d}: {task["projectName"]}')
        index = int(input('输入要刷的课程序号：')) - 1
        task = tasks[index]
        logger.debug(f'已选择：{task["projectName"]} [id:{task["userProjectId"]}]')
        logger.warning('按回车键开始刷课...'), input()
        categories = self.post('https://weiban.mycourse.cn/pharos/usercourse/listCategory.do', data={
            'userProjectId': task['userProjectId'],
            'chooseType': 3
        })['data']
        logger.debug('获取到任务列表：')
        categories_to_flash = []
        for i, cat in enumerate(categories):
            logger.info(f'{i+1: >2d}: {cat["categoryName"]} | 已完成：{cat["finishedNum"]}/{cat["totalNum"]}')
            if cat["finishedNum"] < cat["totalNum"]:
                categories_to_flash.append(cat)
        for cat in categories_to_flash:
            logger.warning(f'正在刷课：{cat["categoryName"]}')
            courses = self.post('https://weiban.mycourse.cn/pharos/usercourse/listCourse.do', {
                'userProjectId': task['userProjectId'],
                'categoryCode': cat['categoryCode'],
                'chooseType': 3,
                'name': ''
            })['data']
            for i, course in enumerate(courses):
                logger.info(f'{i+1: >2d}: {course["resourceName"]}')
                if course['finished'] == 1:
                    logger.debug('该项已完成，跳过')
                    continue
                result = self.post('https://weiban.mycourse.cn/pharos/usercourse/study.do', {
                    'userProjectId': task['userProjectId'],
                    'courseId': course['resourceId']
                })
                logger.debug(f'study.do -> {result}')
                course_url = self.post('https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do', data={
                    'userProjectId': task['userProjectId'],
                    'courseId': course['resourceId']
                })['data']
                logger.debug(f'getCourseUrl.do -> {result}')
                logger.debug(f'getting... -> {self.session.get(course_url).status_code}')
                wait = randint(10, 20)
                logger.debug(f'随机等待 {wait} 秒...')
                sleep(wait)
                result = self.session.post(
                    'https://weiban.mycourse.cn/pharos/usercourse/finish.do', {
                        '_': timestamp(),
                        'userCourseId': course['userCourseId'],
                        'tenantCode': self.userinfo['tenantCode']
                    }
                ).content.decode()
                logger.warning(f'Finishing... -> {result}')
                logger.debug('3 秒后继续下一课程')
                sleep(3)
        logger.warning('全部课程刷课完毕！')


def main():
    logger.warning('使用说明：在电脑浏览器访问 https://weiban.mycourse.cn，然后选择右侧「账号登录」进行登录')
    logger.debug('登录后先完成初始的 10 题考试（如果没有请自动忽略）')
    logger.info('按回车键继续...'), input()
    logger.debug('将下列内容复制到浏览器地址栏并按回车：')
    print('javascript:(function(){data=JSON.parse(localStorage.user);prompt(\'\',JSON.stringify({token:data['
          '\'token\'],userId:data[\'userId\'], tenantCode:data[\'tenantCode\']}));})();')
    logger.warning('（注意某些浏览器会把开头的“javascript:”吞掉，如果粘贴后发现没有请自行补上）')
    userinfo = json.loads(input('把弹窗显示的内容粘贴到这里：'))
    try:
        WeibanClient(userinfo).flash()
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    main()
