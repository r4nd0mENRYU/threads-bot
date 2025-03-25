from playwright.async_api import async_playwright
import asyncio
import json
import os
from time import sleep

async def save_storage_state(context, filename='token.json'):
    """스토리지 상태를 파일로 저장"""
    await context.storage_state(path=filename)
    print(f"✅ 토큰이 {filename}에 저장되었습니다.")

async def save_username(username, filename='usernames.txt'):
    """찾은 사용자 이름을 파일에 저장"""
    with open(filename, 'a') as f:
        f.write(f"{username}\n")
    print(f"✅ 사용자 이름 '{username}'을 {filename}에 저장했습니다.")

async def is_already_followed(username, filename='followed_users.txt'):
    """이미 팔로우한 사용자인지 확인"""
    if not os.path.exists(filename):
        return False
    
    with open(filename, 'r') as f:
        followed_users = f.read().splitlines()
    return username in followed_users

async def save_followed_user(username, filename='followed_users.txt'):
    """팔로우한 사용자 이름을 파일에 저장"""
    with open(filename, 'a') as f:
        f.write(f"{username}\n")
    print(f"✅ 팔로우한 사용자 '{username}'을 {filename}에 저장했습니다")

async def process_post(page, post_index):
    """개별 게시물 처리"""
    try:
        print(f"\n🔄 {post_index + 1}번째 게시물 처리 중...")
        
        # 스크롤을 충분히 내려서 게시물 로딩
        scroll_amount = post_index * 500  # 게시물 높이에 따라 적절히 조정
        print(f"📜 스크롤 위치 조정: {scroll_amount}px")
        await page.evaluate(f"window.scrollTo(0, {scroll_amount})")
        await page.wait_for_timeout(1500)
        
        # 게시물 컨테이너 찾기
        posts_container = page.locator(".x78zum5.xdt5ytf.x13dflua.x11xpdln .x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6").first
        if not await posts_container.is_visible():
            print("❌ 게시물 컨테이너를 찾을 수 없습니다.")
            return False
            
        # 모든 게시물 찾기
        all_posts = await posts_container.locator("div.x78zum5.xdt5ytf").all()
        if post_index >= len(all_posts):
            print(f"❌ {post_index + 1}번째 게시물이 없습니다. 총 게시물 수: {len(all_posts)}")
            return False
            
        # 해당 인덱스의 게시물 선택
        post = all_posts[post_index]
        
        # 게시물이 화면에 보이도록 스크롤
        await post.scroll_into_view_if_needed()
        await page.wait_for_timeout(1000)
        
        if not await post.is_visible():
            print(f"❌ {post_index + 1}번째 게시물이 보이지 않습니다.")
            return False
            
        # 사용자 이름 확인
        try:
            username = await post.locator("span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft").first.text_content()
            print(f"👤 사용자: {username}")
        except Exception as e:
            print(f"❌ 사용자 이름 가져오기 실패: {str(e)}")
            username = f"사용자_{post_index}"
            
        # 1. 팔로우 기능
        try:
            print("🔍 팔로우 버튼 찾는 중...")
            
            # 팔로우 버튼 1: div.x78zum5.xdt5ytf div.xlup9mm.x1kky2od>div>svg
            # 팔로우 유무 div.x78zum5.xdt5ytf div.xlup9mm.x1kky2od div title 의 텍스트가 '팔로잉'이면 이미 팔로우하고 있는 상황
            follow_button = post.locator("div.xlup9mm.x1kky2od > div").first
            
            if await follow_button.is_visible():
                if await follow_button.locator("title").first.text_content() == "팔로우":                    
                    await follow_button.click()
                    print("✅ 팔로우 버튼 클릭 성공")
                    await page.wait_for_timeout(2000)
                    
                    # 모달이 뜨면 팔로우 버튼 2 클릭: div.x1qjc9v5.x7sf2oe.x78zum5.xdt5ytf.x1n2onr6.x1al4vs7 div.x6ikm8r.x10wlt62.xlyipyv
                    follow_confirm = page.locator("div.x1qjc9v5.x7sf2oe.x78zum5.xdt5ytf.x1n2onr6.x1al4vs7 div.x6ikm8r.x10wlt62.xlyipyv").first
                    if await follow_confirm.is_visible():
                        await follow_confirm.click()
                        print("✅ 팔로우 확인 버튼 클릭 성공")
                        await page.wait_for_timeout(2000)
                    
                    # ESC 키를 눌러 모달 닫기
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(1000)
                    
                    # 팔로우한 사용자 저장
                    await save_followed_user(username)
            else:
                print("⚠️ 팔로우 버튼을 찾을 수 없습니다, 이미 팔로우 중입니다.")
                
        except Exception as e:
            print(f"❌ 팔로우 과정 중 오류: {str(e)}")
            
        # 버튼 컨테이너 찾기 (하트, 댓글, 리포스트 버튼이 있는 컨테이너)
        # div.x78zum5.xdt5ytf div.x78zum5.x6s0dn4.x78zum5.xl56j7k.xezivpi
        button_containers = await post.locator("div.x78zum5.x6s0dn4.x78zum5.xl56j7k.xezivpi").all()
        
        if len(button_containers) == 0:
            print("❌ 버튼 컨테이너를 찾을 수 없습니다.")
            return False
            
        print(f"✅ 총 {len(button_containers)}개의 버튼 컨테이너를 찾았습니다.")
        
        # 2. 하트(좋아요) 기능
        try:
            print("💓 하트 버튼 찾는 중... (첫 번째 버튼)")
            # 하트 버튼은 첫 번째 위치에 있음
            
            if len(button_containers) > 0:
                like_button = button_containers[0]
                
                if await like_button.is_visible():
                    # if 하트 버튼이 이미 눌려있으면 누르지 않음
                    # like_button 태그 내에 title 의 텍스트가 '좋아요' 면 아직 눌리지 않은 것. '좋아요 취소' 가 있으면 이미 눌려있는 것
                    # 하트 버튼이 이미 눌렸으면 댓글이나 리포스트도 건너띄고 다음 게시물로 넘어감.

                    if await like_button.locator("title").first.text_content() == "좋아요":
                        await like_button.click()
                        print(f"❤️ {post_index + 1}번째 게시물에 좋아요를 눌렀습니다")
                        await page.wait_for_timeout(2000)
                    else: 
                        print(f"❌ {post_index + 1}번째 게시물에 좋아요가 이미 눌려있습니다. 다음 게시물로 넘어갑니다.")
                        return
                else:
                    print("❌ 하트 버튼이 보이지 않습니다")
            else:
                print("❌ 하트 버튼을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"❌ 하트 버튼 처리 중 오류: {str(e)}")
            
        # 3. 댓글 기능
        try:
            print("💬 댓글 작성 시작... (두 번째 버튼)")
            
            # 댓글 버튼은 두 번째 위치에 있음
            if len(button_containers) > 1:
                comment_button = button_containers[1]
                
                if await comment_button.is_visible():
                    await comment_button.click()
                    print("✅ 댓글 버튼 클릭 성공")
                    await page.wait_for_timeout(2000)
                    
                    # 댓글 입력창 (자동 포커스됨)
                    comment_input = page.locator("div[contenteditable='true']").first
                    if await comment_input.is_visible():
                        comment_text = f"안녕하세요  반갑습니다 😊"
                        await comment_input.fill(comment_text)
                        print(f"✏️ 댓글 입력: {comment_text}")
                        
                        # 게시 버튼 클릭
                        post_button = page.get_by_role("button", name="게시").last
                        if await post_button.is_visible():
                            await post_button.click()
                            print("✅ 댓글을 게시했습니다")
                            await page.wait_for_timeout(3000)
                        else:
                            print("❌ 게시 버튼을 찾을 수 없습니다")
                    else:
                        print("❌ 댓글 입력창을 찾을 수 없습니다")
                else:
                    print("❌ 댓글 버튼이 보이지 않습니다")
            else:
                print("❌ 댓글 버튼이 없습니다 (버튼 컨테이너 수 부족)")
                
        except Exception as e:
            print(f"💬 댓글 작성 중 오류: {str(e)}")
            
        # 4. 리포스트 기능
        try:
            print("🔄 리포스트 시작... (세 번째 버튼)")
            
            # 리포스트 버튼은 세 번째 위치에 있음
            if len(button_containers) > 2:
                repost_button = button_containers[2]
                
                if await repost_button.is_visible():
                    await repost_button.click()
                    print("✅ 리포스트 버튼 클릭 성공")
                    await page.wait_for_timeout(2000)
                    
                    # 리포스트 확인 버튼
                    repost_confirm = page.get_by_role("button", name="리포스트").last
                    if await repost_confirm.is_visible():
                        await repost_confirm.click()
                        print("✅ 리포스트 확인 버튼 클릭 성공")
                        await page.wait_for_timeout(3000)
                    else:
                        print("❌ 리포스트 확인 버튼을 찾을 수 없습니다")
                else:
                    print("❌ 리포스트 버튼이 보이지 않습니다")
            else:
                print("❌ 리포스트 버튼이 없습니다 (버튼 컨테이너 수 부족)")
                
        except Exception as e:
            print(f"🔄 리포스트 중 오류: {str(e)}")
            
        return True
            
    except Exception as e:
        print(f"❌ 게시물 처리 중 오류: {str(e)}")
        return False

async def main():
    async with async_playwright() as p:
        # 계정 정보 설정
        accounts = [
            {"username": "piopio2025y", "password": "consumer..1", "token_file": "token_piopio.json"},
            {"username": "koedits0522", "password": "dkffk1004!", "token_file": "token_koedits.json"}
        ]
        
        # 각 계정마다 페이지 생성 및 작업 수행
        contexts = []
        pages = []
        
        for account in accounts:
            browser_context_args = {}
            
            # 토큰 파일이 있으면 로드
            if os.path.exists(account["token_file"]):
                print(f"💫 {account['username']}의 저장된 토큰을 불러옵니다...")
                browser_context_args['storage_state'] = account["token_file"]
            
            # 브라우저 실행 (첫 번째 계정만 새 브라우저 생성)
            if not contexts:
                browser = await p.chromium.launch(headless=False)
            
            context = await browser.new_context(**browser_context_args)
            contexts.append(context)
            page = await context.new_page()
            pages.append(page)

            # 토큰 파일이 없는 경우에만 로그인 진행
            if not os.path.exists(account["token_file"]):
                print(f"🔑 {account['username']} 계정으로 로그인을 진행합니다...")
                await page.goto('https://www.threads.net/login')
                await page.wait_for_load_state('networkidle')
                
                await page.get_by_placeholder("사용자 이름, 전화번호 또는 이메일 주소").fill(account["username"])
                await page.get_by_placeholder("비밀번호").fill(account["password"])
                
                await page.wait_for_timeout(1000)
                login_button = page.get_by_role("button", name="로그인", exact=True)
                await login_button.first.click()
                
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(10000)
                
                await save_storage_state(context, account["token_file"])
        
        # 무한 루프로 실행
        while True:
            # 각 계정별로 병렬 작업 수행
            for i, (page, account) in enumerate(zip(pages, accounts)):
                print(f"\n🔄 계정 {i+1} ({account['username']}) 세션 시작: 검색 페이지로 이동합니다...")
                await page.goto('https://www.threads.net/search?q=%EC%8A%A4%ED%95%98%EB%A6%AC1000&serp_type=default')
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(5000)  # 페이지 로딩을 위해 대기 시간 증가
                
                # 초기 스크롤 (맨 위로)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(1000)
                
                # 콘텐츠 로드를 위해 스크롤 (약 50개 게시물 로드 목표)
                print(f"📜 계정 {i+1} ({account['username']}): 게시물 로드를 위해 스크롤 중... (약 50개 목표)")
                for j in range(10):  # 10번 스크롤로 약 50개 게시물 로드 목표
                    await page.evaluate(f"window.scrollTo(0, {1000 * (j + 1)})")
                    print(f"스크롤 진행: {j+1}/10")
                    await page.wait_for_timeout(1500)  # 각 스크롤 후 더 오래 기다려 로딩 보장
                
                # 맨 위로 다시 스크롤
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)
                
                # 게시물 컨테이너 찾기
                print(f"📦 계정 {i+1} ({account['username']}): 게시물 컨테이너 찾는 중...")
                posts_container = page.locator(".x78zum5.xdt5ytf.x13dflua.x11xpdln .x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6").first
                if not await posts_container.is_visible():
                    print(f"❌ 계정 {i+1} ({account['username']}): 게시물 컨테이너를 찾을 수 없습니다. 다음 계정으로 넘어갑니다.")
                    continue
                    
                # 게시물 목록 가져오기
                posts = await posts_container.locator("div.x78zum5.xdt5ytf").all()
                post_count = len(posts)
                print(f"✅ 계정 {i+1} ({account['username']}): 총 {post_count}개의 게시물을 찾았습니다.")
                
                if post_count == 0:
                    print(f"❌ 계정 {i+1} ({account['username']}): 게시물을 찾을 수 없습니다. 다음 계정으로 넘어갑니다.")
                    continue
                
                # 처리할 게시물 수 설정 (최대 50개, 실제 찾은 게시물 수 중 작은 값)
                posts_to_process = min(50, post_count)
                processed_count = 0
                
                # 각 게시물 처리
                for j in range(posts_to_process):
                    print("="*50)
                    print(f"📝 계정 {i+1} ({account['username']}): 게시물 #{j+1} 처리 시작")
                    
                    result = await process_post(page, j)
                    if result:
                        processed_count += 1
                        print(f"✅ 처리 성공 ({processed_count}/{posts_to_process})")
                    else:
                        print(f"❌ 처리 실패 ({processed_count}/{posts_to_process})")
                    
                    print(f"📝 계정 {i+1} ({account['username']}): 게시물 #{j+1} 처리 완료")
                    print("="*50)
                    
                    await page.wait_for_timeout(2000)
                
                print(f"\n✅ 계정 {i+1} ({account['username']}): 총 {processed_count}개의 게시물을 처리했습니다.")
                
                # 다음 루프 시작 전 쿠키 유지를 위해 스토리지 업데이트
                await save_storage_state(context, account["token_file"])
            
            print(f"\n🔄 모든 계정 작업 완료. 10초 후 새로고침하여 다시 시작합니다...")
            await page.wait_for_timeout(10000)

if __name__ == "__main__":
    asyncio.run(main()) 