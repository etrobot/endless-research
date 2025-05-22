from app import mission
import logging,sys,traceback,os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

def dailyMission(max_retries = 5):
    for attempt in range(1, max_retries + 1):
        print(f"开始第{attempt}次执行 dailyMission")
        try:
            mission()
            print("dailyMission 成功执行！")
            break
        except Exception as e:
            print(f"dailyMission 第{attempt}次执行失败: {e}")
            rest_time=120
            logging.error(f"[ERROR] dailyMission 执行失败，尝试次数: {attempt}，异常详情: {e},休息{rest_time}分钟再进行下一次尝试")
            __import__('time').sleep(rest_time)
            if attempt == max_retries:
                logging.info(f"重试次数已达{max_retries}次，退出！")


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
