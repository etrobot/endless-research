from app import mission
import logging,sys,traceback,os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

def dailyMission(max_retries = 10):
    for attempt in range(1, max_retries + 1):
        print(f"开始第{attempt}次执行 dailyMission")
        try:
            mission()
            print("dailyMission 成功执行！")
            break
        except Exception as e:
            print(f"dailyMission 第{attempt}次执行失败: {e}")
            logging.error(f"[ERROR] dailyMission 执行失败，尝试次数: {attempt}，异常详情: {e}")
            logging.info(f"[INFO] 当前异常后将休息 60 秒（休息一分钟）再进行下一次尝试，尝试次数: {attempt}")
            __import__('time').sleep(60)
            if attempt == max_retries:
                print("重试次数已达10次，退出！")


if __name__ == "__main__":
    if os.getenv('TESTING'):
        mission()
        exit()
    scheduler = BlockingScheduler(timezone=timezone('UTC'))
    try:
        scheduler.add_job(
            dailyMission,
            trigger=CronTrigger(
                hour='*',      # 每小时
                minute=0       # 整点
            ),
            name='daily_notion_mission'
        )
        logging.info(f"[定时任务] 服务已启动，每小时整点执行任务（UTC时间）")
        scheduler.start()
    except Exception as e:
        error_msg = f"启动定时任务失败: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"[定时任务] {error_msg}")
        sys.exit(1)
