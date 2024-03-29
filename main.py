import getpass
import io
import os
import json
import base64
import time
import random
import requests
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
from threading import Thread
from datetime import datetime
from dotenv import load_dotenv # 用来加载环境变量

load_dotenv()  # 加载 .env 文件中的环境变量


UPLOAD_FOLDER = 'images'
API_SERVER_IP = os.environ.get('API_SERVER_IP') # 【获取系统 ip 方法一(硬编码)】=> 从环境变量中获取 API_SERVER_IP -> (🚀 部署后记得更换为服务器的 IP！)
COMFYUI_OUTPUT_PATH = os.environ.get('COMFYUI_OUTPUT_PATH') # 生成后的图片存放路径
URL = f"http://{API_SERVER_IP}:8188" # comfyUI 的服务器地址
PORT = 5001 # 服务器端口, 必须跟服务器启动的端口号一样(比如 5001), 用于生成图片的 URL
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # 指定图片存储文件夹的路径
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # 确保上传文件夹存在


# ⌛️ 轮询方法, 等待生图完成 ————————————————————————————————————————————————————————————————————————
def check_image_status(prompt_id, timeout=720, interval=2):
    # 检查图片状态, 直到生成完图片或者图片生成超时
    stast_time = time.time()
    request_time = 0 # 请求次数
    while time.time() - stast_time < timeout: # 当前时间 - 开始时间 < 超时时间
        try:
            request_time += 1
            img_response = requests.get(url=f'{URL}/history/{prompt_id}') # 请求生图结果
            print(f"⏰ 请求了{request_time}次生图结果...")
            if img_response.status_code == 200:
                data = img_response.json().get(prompt_id, {}).get('outputs', {}) # 等价于 data = img_response_data.json()[prompt_id], 但这种方式有弊端, 如果 output 不存在会报错  <==  看下返回的 outputs 在哪个节点号！ => 哪个节点有 image
                if data:
                    return jsonify(data) # flask 的 jsonify() 方法可以将字典转换为 json 字符串
            time.sleep(interval) # 每隔 interval 秒轮询一次
        except Exception as e:
            return jsonify({"❌ 生图出错: ", str(e)}), 404
    return jsonify({"❌ 生图超时: ": str(e)}), 404
			
   
# 将图片数据转换为 base64 编码的格式
def encode_pil_to_base64(image): # 给图像编码
    with io.BytesIO() as output_bytes:
        image.save(output_bytes, format="jpg")
        bytes_data = output_bytes.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")


# 生成 images 静态图片文件夹 url 的方法
@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 生成 comfyUI 的 output 静态图片文件夹 url 的方法
@app.route('/output/<filename>')
def comfyUI_output(filename):
	username = getpass.getuser() # 获取当前电脑的用户名（实际的图片存在这个文件夹内）
	# output_folder = f'/Users/{username}/ComfyUI/output'
	output_folder = COMFYUI_OUTPUT_PATH
	return send_from_directory(output_folder, filename)

# 拿到上传图片并开始生成后, 删除图片的方法
def remove_upload_imagses(*file_paths):
	for file_path in file_paths:
		try:
			os.remove(file_path)
			print(f"✅ 删除了上传后的图片: {file_path}")
		except Exception as e:
			print(f"❌ 图片删除失败: {file_path}, {e}")

# 生图服务的路由 ————————————————————————————————————————————————————————————————————————————————————————————————————————
@app.route('/generate', methods=['POST'])
def index():
    # 从 【post】请求中获取 【2 张图片】
    image_file_1 = request.files.get('image1') # 获取第一张图片的二进制流
    image_file_2 = request.files.get('image2') # 获取第二张图片的二进制流
    
    if not image_file_1 or not image_file_2:
        return jsonify({"error": "❌ 缺失 2 张图片"}), 404
    else: # 返回数据
        # 读取图片文件
        image_data_1 = request.files.get('image1')
        image_data_2 = request.files.get('image2')
        # image_data_1 = image_file_1.read()
        # image_data_2 = image_file_2.read()
        print("✅ 解码图片成功", image_file_1, image_file_2)
        print("————————————————————————————————————————————————")
        
        # 生成随机数
        random_number_A = random.randint(0, 10000)
        random_number_B = random.randint(10001, 20000)
        fileName_1 = f'uploaded_image_{random_number_A}.jpg'
        fileName_2 = f'uploaded_image_{random_number_B}.jpg'
        filePath_1 = os.path.join(app.config['UPLOAD_FOLDER'], fileName_1) # flask 会自动创建一个 static 文件夹, 用于存放静态文件
        filePath_2 = os.path.join(app.config['UPLOAD_FOLDER'], fileName_2) # flask 会自动创建一个 static 文件夹, 用于存放静态文件
        image_data_1.save(filePath_1) # 保存图片
        image_data_2.save(filePath_2) # 保存图片
        absoluteFilePath_1 = os.path.abspath(filePath_1)
        absoluteFilePath_2 = os.path.abspath(filePath_2)
        print("✅ 保存图片成功", absoluteFilePath_1, absoluteFilePath_2)
        print("————————————————————————————————————————————————")
        
        # 将保存路径转换为图片的 URL
        # img_url_1 = f'http://{API_SERVER_IP}:{PORT}/images/{os.path.basename(filePath_1)}'
        # img_url_2 = f'http://{API_SERVER_IP}:{PORT}/images/{os.path.basename(filePath_2)}'
        # print("✅ 拿到了两张图片的 url: ", img_url_1, img_url_2)
        # print("————————————————————————————————————————————————")
        
        # 将图片数据转换为二进制字符串, latin-1 表示每个字符占用一个字节
        # image_string_1 = image_data_1.decode('latin-1')
        # image_string_2 = image_data_2.decode('latin-1')
        
        # 将图片转为 base64 编码的格式
        # mg_encode_1  = Image.open(io.BytesIO(image_string_1))
        # mg_encode_2  = Image.open(io.BytesIO(image_string_2))
        # image_base64_1 = encode_pil_to_base64(image_string_1)
        # image_base64_2 = encode_pil_to_base64(image_string_2)
        # print("✅ 拿到了两张图片的 base64: ", image_base64_1, image_base64_2)
        # print("————————————————————————————————————————————————")
        
        # 打开 json 工作流
        # 获取当前文件所在的目录（即main.py所在的目录）
        current_directory = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_directory, 'prompt', 'flow.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            prompt_dict = json.loads(f.read()) # 直接以 json 形式进行读取
            
            # 修改 prompt 字典中的图片数据 -> 修改 json 数据
            prompt_dict["139"]["inputs"]["image"] = absoluteFilePath_1 # 修改第一张图片
            prompt_dict["144"]["inputs"]["image"] = absoluteFilePath_2 # 修改第一张图片
            # return (img_url_1)
            

		    # ✏️ 文生图 - 【发送生图请求】 ————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————        
            # 发送请求, 开始进入队列进行生图, 接口会返回一个生图队列的 id
            response = requests.post(url=f'{URL}/prompt', json={"prompt": prompt_dict}) # 把提示词替换为传入的 flow.json
            # 确保响应状态码为200（成功）
            if response.status_code == 200:
                response_jsonData = response.json() # 不会马上响应, 只会返回个队列 ID , 如果有 id 了则是生成好了图片
        
                #  获得下发的生图任务 id
                time.sleep(5)
                # 检查 response_jsonData 是否包含'prompt_id'
                if "prompt_id" in response_jsonData:
                    prompt_id = response_jsonData["prompt_id"]
                    print("✅ 返回了任务 id: ", prompt_id)
                    print("————————————————————————————————————————————————")

  		        # 查看下 output
                if prompt_id:
                    try:
                        # 【获得生图结果】
                        res = ''
                        res = check_image_status(prompt_id)
                        res_data = res.get_json() # 在 Flask 中, 当使用 jsonify() 创建一个响应时，实际上是返回了一个 Flask Response 对象, 其中包含了 JSON 格式的字符串作为其数据。要访问这个数据, 需要先检查响应的状态码, 然后解析响应内容为 JSON
                        print("👀 拿到了生图结果: ", res_data)
                        print("————————————————————————————————————————————————")
                
						# 获得 ComfyUI 生完图的图片名称
                        img_name = res_data['138']['images'][0]['filename']
                        
                        
                        # 使用 view 预览接口来获取图片信息（实际上并不是图片的绝对地址！！只是 comfyUI 服务器提供的预览）
                        # view_image_path = f'{URL}/view?filename={img_name}'  # (图片实际上保存在 ComfyUI 的 output 文件夹)
                        # print("👍 预览图片: ", view_image_path)
                        # print("————————————————————————————————————————————————")
                        
                        # ComfyUI 存放图片的文件夹路径
                        img_url = f'http://{API_SERVER_IP}:{PORT}/output/{img_name}'
                        print("👍 生成了图片地址: ", img_url)
                        remove_upload_imagses(filePath_1, filePath_2) # 删除上传的图片, 释放空间
                        return img_url
    
                    except Exception as e:
                        return jsonify({"❌ Error": str(e)}), 404
                else:
                    return jsonify({"❌ Error": "生图失败"}), 404
                

# 初始化 __main__
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=5001, debug=True)


