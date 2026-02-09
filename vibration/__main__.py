"""python -m vibration 진입점."""
import multiprocessing

if __name__ == "__main__":
    # PyInstaller Windows exe에서 ProcessPoolExecutor 사용 시 필수.
    # 없으면 워커 프로세스마다 메인 모듈을 재실행하여 창이 여러 개 뜸.
    multiprocessing.freeze_support()

    from vibration.app import main
    main()
