from playwright.async_api import async_playwright
import asyncio
import json
import os
import random
from time import sleep

# 프록시 리스트에서 무작위로 프록시 선택
def get_random_proxies(num_proxies=3, file_path='proxy_list.txt'):
    with open(file_path, 'r') as f:
        proxies = f.read().splitlines()
    
    # 무작위로 프록시 3개 선택
    selected_proxies = random.sample(proxies, min(num_proxies, len(proxies)))
    
    # 프록시 포맷: IP:PORT:USERNAME:PASSWORD
    formatted_proxies = []
    for proxy in selected_proxies:
        parts = proxy.split(':')
        if len(parts) == 4:
            formatted_proxies.append({
                'server': f"{parts[0]}:{parts[1]}",
                #  아이디 비밀번호 필드 없음.
                'username': parts[2],
                'password': parts[3]
            })
    
    return formatted_proxies

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

async def process_post(page, post_index, proxy_info=None):
    """개별 게시물 처리"""
    proxy_text = f"[프록시: {proxy_info['server']}] " if proxy_info else ""
    
    try:
        print(f"\n🔄 {proxy_text}{post_index + 1}번째 게시물 처리 중...")
        
        # 스크롤을 충분히 내려서 게시물 로딩 - 프록시 사용 시 더 긴 대기 시간 필요
        scroll_amount = post_index * 500  # 게시물 높이에 따라 적절히 조정
        print(f"📜 {proxy_text}스크롤 위치 조정: {scroll_amount}px")
        await page.evaluate(f"window.scrollTo(0, {scroll_amount})")
        await page.wait_for_timeout(3000)  # 프록시 사용 시 대기 시간 증가
        
        # 게시물 컨테이너 찾기
        posts_container = page.locator(".x78zum5.xdt5ytf.x13dflua.x11xpdln .x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6").first
        if not await posts_container.is_visible(timeout=10000):  # 타임아웃 증가
            print(f"❌ {proxy_text}게시물 컨테이너를 찾을 수 없습니다.")
            return False
            
        # 모든 게시물 찾기
        all_posts = await posts_container.locator("div.x78zum5.xdt5ytf").all()
        if post_index >= len(all_posts):
            print(f"❌ {proxy_text}{post_index + 1}번째 게시물이 없습니다. 총 게시물 수: {len(all_posts)}")
            return False
            
        # 해당 인덱스의 게시물 선택
        post = all_posts[post_index]
        
        # 게시물이 화면에 보이도록 스크롤
        await post.scroll_into_view_if_needed()
        await page.wait_for_timeout(2000)  # 프록시 사용 시 대기 시간 증가
        
        if not await post.is_visible(timeout=5000):  # 타임아웃 증가
            print(f"❌ {proxy_text}{post_index + 1}번째 게시물이 보이지 않습니다.")
            return False
            
        # 사용자 이름 확인
        try:
            username = await post.locator("span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft").first.text_content(timeout=5000)
            print(f"👤 {proxy_text}사용자: {username}")
        except Exception as e:
            print(f"❌ {proxy_text}사용자 이름 가져오기 실패: {str(e)}")
            username = f"사용자_{post_index}"
            
        # 1. 팔로우 기능
        try:
            print(f"🔍 {proxy_text}팔로우 버튼 찾는 중...")
            
            # 팔로우 버튼 1: div.x78zum5.xdt5ytf div.xlup9mm.x1kky2od>div>svg
            follow_button = post.locator("div.xlup9mm.x1kky2od > div").first
            
            if await follow_button.is_visible(timeout=5000):
                if await follow_button.locator("title").first.text_content(timeout=5000) == "팔로우":                    
                    await follow_button.click(timeout=5000)
                    print(f"✅ {proxy_text}팔로우 버튼 클릭 성공")
                    await page.wait_for_timeout(4000)  # 프록시 사용 시 대기 시간 증가
                    
                    # 모달이 뜨면 팔로우 버튼 2 클릭: div.x1qjc9v5.x7sf2oe.x78zum5.xdt5ytf.x1n2onr6.x1al4vs7 div.x6ikm8r.x10wlt62.xlyipyv
                    follow_confirm = page.locator("div.x1qjc9v5.x7sf2oe.x78zum5.xdt5ytf.x1n2onr6.x1al4vs7 div.x6ikm8r.x10wlt62.xlyipyv").first
                    if await follow_confirm.is_visible(timeout=5000):
                        await follow_confirm.click(timeout=5000)
                        print(f"✅ {proxy_text}팔로우 확인 버튼 클릭 성공")
                        await page.wait_for_timeout(4000)
                    
                    # ESC 키를 눌러 모달 닫기
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(2000)
                    
                    # 팔로우한 사용자 저장
                    await save_followed_user(username)
            else:
                print(f"⚠️ {proxy_text}팔로우 버튼을 찾을 수 없습니다, 이미 팔로우 중입니다.")
                
        except Exception as e:
            print(f"❌ {proxy_text}팔로우 과정 중 오류: {str(e)}")
            
        # 버튼 컨테이너 찾기 (하트, 댓글, 리포스트 버튼이 있는 컨테이너)
        button_containers = await post.locator("div.x78zum5.x6s0dn4.x78zum5.xl56j7k.xezivpi").all()
        
        if len(button_containers) == 0:
            print(f"❌ {proxy_text}버튼 컨테이너를 찾을 수 없습니다.")
            return False
            
        print(f"✅ {proxy_text}총 {len(button_containers)}개의 버튼 컨테이너를 찾았습니다.")
        
        # 2. 하트(좋아요) 기능
        try:
            print(f"💓 {proxy_text}하트 버튼 찾는 중... (첫 번째 버튼)")
            # 하트 버튼은 첫 번째 위치에 있음
            
            if len(button_containers) > 0:
                like_button = button_containers[0]
                
                if await like_button.is_visible(timeout=5000):
                    # 하트 버튼이 눌려있는지 확인
                    if await like_button.locator("title").first.text_content(timeout=5000) == "좋아요":
                        await like_button.click(timeout=5000)
                        print(f"❤️ {proxy_text}{post_index + 1}번째 게시물에 좋아요를 눌렀습니다")
                        await page.wait_for_timeout(3000)
                    else: 
                        print(f"❌ {proxy_text}{post_index + 1}번째 게시물에 좋아요가 이미 눌려있습니다. 다음 게시물로 넘어갑니다.")
                        return
                else:
                    print(f"❌ {proxy_text}하트 버튼이 보이지 않습니다")
            else:
                print(f"❌ {proxy_text}하트 버튼을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"❌ {proxy_text}하트 버튼 처리 중 오류: {str(e)}")
            
        # 3. 댓글 기능
        try:
            print(f"💬 {proxy_text}댓글 작성 시작... (두 번째 버튼)")
            
            # 댓글 버튼은 두 번째 위치에 있음
            if len(button_containers) > 1:
                comment_button = button_containers[1]
                
                if await comment_button.is_visible(timeout=5000):
                    await comment_button.click(timeout=5000)
                    print(f"✅ {proxy_text}댓글 버튼 클릭 성공")
                    await page.wait_for_timeout(4000)  # 프록시 사용 시 대기 시간 증가
                    
                    # 댓글 입력창 (자동 포커스됨)
                    comment_input = page.locator("div[contenteditable='true']").first
                    if await comment_input.is_visible(timeout=5000):
                        comment_text = f"안녕하세요  반갑습니다 😊"
                        await comment_input.fill(comment_text, timeout=5000)
                        print(f"✏️ {proxy_text}댓글 입력: {comment_text}")
                        
                        # 게시 버튼 클릭
                        post_button = page.get_by_role("button", name="게시").last
                        if await post_button.is_visible(timeout=5000):
                            await post_button.click(timeout=5000)
                            print(f"✅ {proxy_text}댓글을 게시했습니다")
                            await page.wait_for_timeout(5000)  # 프록시 사용 시 대기 시간 증가
                        else:
                            print(f"❌ {proxy_text}게시 버튼을 찾을 수 없습니다")
                    else:
                        print(f"❌ {proxy_text}댓글 입력창을 찾을 수 없습니다")
                else:
                    print(f"❌ {proxy_text}댓글 버튼이 보이지 않습니다")
            else:
                print(f"❌ {proxy_text}댓글 버튼이 없습니다 (버튼 컨테이너 수 부족)")
                
        except Exception as e:
            print(f"💬 {proxy_text}댓글 작성 중 오류: {str(e)}")
            
        # 4. 리포스트 기능
        try:
            print(f"🔄 {proxy_text}리포스트 시작... (세 번째 버튼)")
            
            # 리포스트 버튼은 세 번째 위치에 있음
            if len(button_containers) > 2:
                repost_button = button_containers[2]
                
                if await repost_button.is_visible(timeout=5000):
                    await repost_button.click(timeout=5000)
                    print(f"✅ {proxy_text}리포스트 버튼 클릭 성공")
                    await page.wait_for_timeout(4000)  # 프록시 사용 시 대기 시간 증가
                    
                    # 리포스트 확인 버튼
                    repost_confirm = page.get_by_role("button", name="리포스트").last
                    if await repost_confirm.is_visible(timeout=5000):
                        await repost_confirm.click(timeout=5000)
                        print(f"✅ {proxy_text}리포스트 확인 버튼 클릭 성공")
                        await page.wait_for_timeout(5000)  # 프록시 사용 시 대기 시간 증가
                    else:
                        print(f"❌ {proxy_text}리포스트 확인 버튼을 찾을 수 없습니다")
                else:
                    print(f"❌ {proxy_text}리포스트 버튼이 보이지 않습니다")
            else:
                print(f"❌ {proxy_text}리포스트 버튼이 없습니다 (버튼 컨테이너 수 부족)")
                
        except Exception as e:
            print(f"🔄 {proxy_text}리포스트 중 오류: {str(e)}")
            
        return True
            
    except Exception as e:
        print(f"❌ {proxy_text}게시물 처리 중 오류: {str(e)}")
        return False

async def run_session(proxy_info, proxy_index):
    """각 프록시에 대한 개별 세션 실행"""
    async with async_playwright() as p:
        browser_context_args = {
            # 프록시 설정
            'proxy': {
                'server': proxy_info['server'],
                'username': proxy_info['username'],
                'password': proxy_info['password'],
            },
            # 브라우저 언어 설정을 한국어로
            'locale': 'ko-KR',
        }
        
        # token.json이 있으면 로드
        token_file = f'token_proxy_{proxy_index}.json'
        if os.path.exists(token_file):
            print(f"💫 [프록시: {proxy_info['server']}] 저장된 토큰을 불러옵니다...")
            browser_context_args['storage_state'] = token_file
        
        # 브라우저 실행 (언어 설정 추가)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(**browser_context_args)
        
        # 언어 설정을 한국어로 설정
        await context.set_extra_http_headers({"Accept-Language": "ko-KR,ko;q=0.9"})
        
        page = await context.new_page()

        # 로그인이 필요한 경우에만 로그인 진행
        if not os.path.exists(token_file):
            print(f"🔑 [프록시: {proxy_info['server']}] 로그인을 진행합니다...")
            await page.goto('https://www.threads.net/login', timeout=60000)  # 타임아웃 증가
            await page.wait_for_load_state('networkidle', timeout=60000)  # 타임아웃 증가
            
            # 프록시 접속이 느리므로 대기 시간 증가
            await page.wait_for_timeout(5000)
            
            await page.get_by_placeholder("사용자 이름, 전화번호 또는 이메일 주소").fill("piopio2025y", timeout=10000)
            await page.get_by_placeholder("비밀번호").fill("consumer..1", timeout=10000)
            
            await page.wait_for_timeout(2000)
            login_button = page.get_by_role("button", name="로그인", exact=True)
            await login_button.first.click(timeout=10000)
            
            await page.wait_for_load_state('networkidle', timeout=60000)  # 타임아웃 증가
            await page.wait_for_timeout(15000)  # 프록시 사용 시 더 긴 대기 시간 필요
            
            await save_storage_state(context, token_file)
        
        try:
            # 세션 반복 횟수 설정
            session_count = 0
            max_sessions = 3  # 세션 최대 실행 횟수
            
            # 무한 루프로 실행
            while session_count < max_sessions:
                session_count += 1
                print(f"\n🔄 [프록시: {proxy_info['server']}] 세션 {session_count}/{max_sessions} 시작")
                
                # 검색 페이지로 이동
                print(f"\n🔄 [프록시: {proxy_info['server']}] 새 세션 시작: 검색 페이지로 이동합니다...")
                await page.goto('https://www.threads.net/search?q=%EC%8A%A4%ED%95%98%EB%A6%AC1000&serp_type=default', timeout=60000)  # 타임아웃 증가
                await page.wait_for_load_state('networkidle', timeout=60000)  # 타임아웃 증가
                await page.wait_for_timeout(8000)  # 프록시 사용 시 더 긴 대기 시간 필요
                
                # 초기 스크롤 (맨 위로)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)
                
                # 콘텐츠 로드를 위해 스크롤 (약 20개 게시물 로드 목표)
                print(f"📜 [프록시: {proxy_info['server']}] 게시물 로드를 위해 스크롤 중... (약 20개 목표)")
                for i in range(5):  # 5번 스크롤로 약 20개 게시물 로드 목표 (프록시 사용 시 더 적게)
                    await page.evaluate(f"window.scrollTo(0, {1000 * (i + 1)})")
                    print(f"[프록시: {proxy_info['server']}] 스크롤 진행: {i+1}/5")
                    await page.wait_for_timeout(3000)  # 프록시 사용 시 더 긴 대기 시간 필요
                
                # 맨 위로 다시 스크롤
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(3000)
                
                # 게시물 컨테이너 찾기
                print(f"📦 [프록시: {proxy_info['server']}] 게시물 컨테이너 찾는 중...")
                posts_container = page.locator(".x78zum5.xdt5ytf.x13dflua.x11xpdln .x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6").first
                if not await posts_container.is_visible(timeout=10000):  # 타임아웃 증가
                    print(f"❌ [프록시: {proxy_info['server']}] 게시물 컨테이너를 찾을 수 없습니다. 다시 시도합니다.")
                    continue
                    
                # 게시물 목록 가져오기
                posts = await posts_container.locator("div.x78zum5.xdt5ytf").all()
                post_count = len(posts)
                print(f"✅ [프록시: {proxy_info['server']}] 총 {post_count}개의 게시물을 찾았습니다.")
                
                if post_count == 0:
                    print(f"❌ [프록시: {proxy_info['server']}] 게시물을 찾을 수 없습니다. 다시 시도합니다.")
                    continue
                
                # 처리할 게시물 수 설정 (최대 10개, 실제 찾은 게시물 수 중 작은 값)
                # 프록시 사용 시 처리할 게시물 수를 줄여 더 효율적으로 작업
                posts_to_process = min(10, post_count)
                processed_count = 0
                
                # 각 게시물 처리
                for i in range(posts_to_process):
                    print("="*50)
                    print(f"📝 [프록시: {proxy_info['server']}] 게시물 #{i+1} 처리 시작")
                    
                    result = await process_post(page, i, proxy_info)
                    if result:
                        processed_count += 1
                        print(f"✅ [프록시: {proxy_info['server']}] 처리 성공 ({processed_count}/{posts_to_process})")
                    else:
                        print(f"❌ [프록시: {proxy_info['server']}] 처리 실패 ({processed_count}/{posts_to_process})")
                    
                    print(f"📝 [프록시: {proxy_info['server']}] 게시물 #{i+1} 처리 완료")
                    print("="*50)
                    
                    await page.wait_for_timeout(3000)  # 프록시 사용 시 더 긴 대기 시간 필요
                
                print(f"\n✅ [프록시: {proxy_info['server']}] 총 {processed_count}개의 게시물을 처리했습니다.")
                print(f"🔄 [프록시: {proxy_info['server']}] 15초 후 새로고침하여 다시 시작합니다...")
                await page.wait_for_timeout(15000)  # 프록시 사용 시 더 긴 대기 시간 필요
                
                # 다음 루프 시작 전 쿠키 유지를 위해 스토리지 업데이트
                await save_storage_state(context, token_file)
                
            print(f"✅ [프록시: {proxy_info['server']}] 모든 세션({max_sessions}개)을 완료했습니다.")
                
        except Exception as e:
            print(f"❌ [프록시: {proxy_info['server']}] 세션 실행 중 오류 발생: {str(e)}")
        
        finally:
            # 브라우저 종료
            await browser.close()
            print(f"🔒 [프록시: {proxy_info['server']}] 브라우저를 종료했습니다.")

async def main():
    # 프록시 리스트에서 3개의 프록시 무작위 선택
    proxies = get_random_proxies(3)
    print(f"🔄 선택된 프록시: {[proxy['server'] for proxy in proxies]}")
    
    # 각 프록시별로 별도의 태스크 생성
    tasks = []
    for i, proxy in enumerate(proxies):
        tasks.append(run_session(proxy, i))
    
    # 모든 태스크 동시 실행
    await asyncio.gather(*tasks)
    
    print("✅ 모든 프록시 세션이 완료되었습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 