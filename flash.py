import sys
import json
import requests
import tkinter as tk
from io import BytesIO
from loguru import logger
from random import randint
from time import time, sleep
from PIL import Image, ImageTk

logger.remove()
logger.add(sys.stdout, format='<level>[{time:HH:MM:SS}] {message}</level>')


def timestamp():
    return f'{int(time())}'


class WeibanClient(object):
    def __init__(self):
        self.userinfo = {}
        self.session = requests.session()
        self.current_request = None
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/93.0.4544.0 Safari/537.36'
        })
        self.last_choice = {}

    def login_with_qrcode(self):
        logger.debug('正在获取二维码...')
        qrcode = self.session.get('https://weiban.mycourse.cn/pharos/login/genBarCodeImageAndCacheUuid.do', params={
            'timestamp': timestamp()
        }).json()['data']
        image = Image.open(BytesIO(self.session.get(qrcode['imagePath']).content))
        logger.debug('请扫码完成登录')
        root = tk.Tk()
        root.title('扫码登录后关闭此窗口')
        image = ImageTk.PhotoImage(image)
        tk.Label(root, image=image).pack()
        root.lift()
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        root.mainloop()
        sleep(3)
        result = self.post('https://weiban.mycourse.cn/pharos/login/barCodeWebAutoLogin.do', {
            'barCodeCacheUserId': qrcode['barCodeCacheUserId']
        })['data']
        self.userinfo = {key: result[key] for key in result if key in ('token', 'userId', 'tenantCode')}
        logger.warning('登录成功！')

    def login_with_password(self):
        pass

    def login_manually(self):
        logger.debug('将下列内容复制到浏览器地址栏并按回车：')
        print('javascript:(function(){data=JSON.parse(localStorage.user);prompt(\'\',JSON.stringify({token:data['
              '\'token\'],userId:data[\'userId\'], tenantCode:data[\'tenantCode\']}));})();')
        logger.warning('（注意某些浏览器会把开头的“javascript:”吞掉，如果粘贴后发现没有请自行补上）')
        self.userinfo = json.loads(input('把弹窗显示的内容粘贴到这里：'))

    def post(self, url, data={}):
        return self.session.post(url, params={'timestamp': timestamp()}, data={
            **self.userinfo,
            **data
        }).json()

    def list_study_task(self):
        return self.post('https://weiban.mycourse.cn/pharos/index/listStudyTask.do')['data']

    def list_category(self, user_project_id):
        categories = []
        for T in (3, 1, 2):
            result = self.post('https://weiban.mycourse.cn/pharos/usercourse/listCategory.do', data={
                'userProjectId': user_project_id,
                'chooseType': T
            })['data']
            categories.append(result)
        return categories

    def list_courses(self, user_project_id, category_code, choose_type):
        return self.post('https://weiban.mycourse.cn/pharos/usercourse/listCourse.do', {
            'userProjectId': user_project_id,
            'categoryCode': category_code,
            'chooseType': choose_type,
            'name': ''
        })['data']

    def start_study(self, user_project_id, resource_id):
        result = self.post('https://weiban.mycourse.cn/pharos/usercourse/study.do', {
            'userProjectId': user_project_id,
            'courseId': resource_id
        })
        logger.info(f'study.do -> {result}')
        course_url = self.post('https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do', data={
            'userProjectId': user_project_id,
            'courseId': resource_id
        })['data']
        logger.info(f'getCourseUrl.do -> {result}')
        logger.info(f'getting... -> {self.session.get(course_url).status_code}')

    def send_finish(self, user_course_id):
        return self.session.post(
            'https://weiban.mycourse.cn/pharos/usercourse/finish.do', {
                '_': timestamp(),
                'userCourseId': user_course_id,
                'tenantCode': self.userinfo['tenantCode']
            }
        ).content.decode()

    def show_progress(self, user_project_id):
        return self.post('https://weiban.mycourse.cn/pharos/project/showProgress.do', {
            'userProjectId': user_project_id
        })['data']

    def optional_finished(self, user_project_id):
        progress = self.show_progress(user_project_id)
        return progress['optionalFinishedNum'] >= progress['optionalNum']

    def flash(self):
        tasks = self.list_study_task()
        logger.debug('发现课程列表：')
        for i, task in enumerate(tasks):
            logger.info(f'{i+1: >2d}: {task["projectName"]}')
        if len(tasks) > 1:
            if 'index' in self.last_choice:
                index = self.last_choice['index']
            else:
                index = int(input('输入要刷的课程序号：')) - 1
                self.last_choice['index'] = index
        else:
            index = 0
        task = tasks[index]
        logger.debug(f'已选择：{task["projectName"]} [id:{task["userProjectId"]}]')
        if '-y' not in self.last_choice:
            logger.warning('确认开始刷课吗？'), input()
            self.last_choice['-y'] = True
        categories = self.list_category(task['userProjectId'])
        for T, name in enumerate(('必修课程', '匹配课程', '自选课程')):
            logger.debug(f'获取到任务列表 [{name}]：')
            categories_to_flash = []
            for i, cat in enumerate(categories[T]):
                logger.info(f'{i+1: >2d}: {cat["categoryName"]} | 已完成：{cat["finishedNum"]}/{cat["totalNum"]}')
                if cat["finishedNum"] < cat["totalNum"]:
                    categories_to_flash.append(cat)
            if not categories_to_flash:
                logger.warning('该课程已完成，跳过')
                continue
            if name == '自选课程' and self.optional_finished(task['userProjectId']):
                logger.warning('自选课程已完成！')
                continue
            for cat in categories_to_flash:
                logger.warning(f'正在刷课：{name} -> {cat["categoryName"]}')
                courses = self.list_courses(task['userProjectId'], cat['categoryCode'], (3, 1, 2)[T])
                for i, course in enumerate(courses):
                    logger.debug(f'{i+1: >2d}: {course["resourceName"]}')
                    if course['finished'] == 1:
                        logger.debug('该项已完成，跳过')
                        continue
                    self.start_study(task['userProjectId'], course['resourceId'])
                    wait = randint(10, 20)
                    logger.warning(f'随机等待 {wait} 秒...')
                    sleep(wait)
                    logger.debug(f'Finishing... -> {self.send_finish(course["userCourseId"])}')
                    logger.debug('3 秒后继续下一课程')
                    sleep(3)
        progress = self.show_progress(task['userProjectId'])
        logger.debug('必修课程：[{requiredFinishedNum}/{requiredNum}] | 匹配课程：[{pushFinishedNum}/{pushNum}] | 自选课程：[{'
                     'optionalFinishedNum}/{optionalNum}]'.format(**progress))
        logger.warning('全部课程刷课完毕！')
        input()


def main():
    logger.warning('使用说明：在电脑浏览器访问 https://weiban.mycourse.cn，然后选择右侧「账号登录」进行登录')
    logger.debug('登录后先完成初始的 10 题考试（如果没有请自动忽略）')
    logger.info('按回车键继续...'), input()

    logger.debug('请选择登录方式：')
    for i, method in enumerate(('扫码登录（默认）', '手动登录')):
        logger.info(f'{i+1}: {method}')
    client = WeibanClient()
    method = int(input() or '1')
    if method == 1:
        client.login_with_qrcode()
    elif method == 2:
        client.login_manually()
    else:
        logger.error('What?')
        exit()
    for trial in range(10):
        try:
            client.flash()
            break
        except Exception as err:
            logger.error(repr(err))
            logger.warning('发生错误，5 秒后重试')
            sleep(5)
    else:
        logger.error('重试次数过多！')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.warning('Exiting...')
    except KeyboardInterrupt:
        logger.warning('Exiting...')
