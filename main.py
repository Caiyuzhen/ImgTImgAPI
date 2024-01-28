import io
import os
import json
import base64
import time
import random
import requests
from PIL import Image
from flask import Flask, request, jsonify
from threading import Thread
from datetime import datetime


url = "http://127.0.0.1:8188" # comfyUI 的服务器地址
app = Flask(__name__)
IMG_ID = None
UPLOAD_FOLDER = 'uploadImageFolder'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # 指定图片存储文件夹的路径
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # 确保上传文件夹存在


# ⌛️ 轮询方法, 等待生图完成 ————————————————————————————————————————————————————————————————————————
def check_image_status(prompt_id, timeout=60, interval=2):
    """检查图片状态, 直到生成完图片或者图片生成超时"""
    stast_time = time.time()
    while time.time() - stast_time < timeout: # 当前时间 - 开始时间 < 超时时间
        img_response = requests.get(url=f'{url}/history/{prompt_id}') # 请求生图结果
        if img_response.status_code == 200:
            data = img_response.json().get(prompt_id, {}).get('outputs', {}) # 等价于 data = img_response_data.json()[prompt_id], 但这种方式有弊端, 如果 output 不存在会报错  <==  看下返回的 outputs 在哪个节点号！ => 哪个节点有 image
            if data:
                return jsonify(data) # flask 的 jsonify() 方法可以将字典转换为 json 字符串
        time.sleep(interval) # 每隔 interval 秒轮询一次
			
   
# 将图片数据转换为 base64 编码的格式
def encode_image_to_base64(image_data):
    return base64.b64encode(image_data).decode('utf-8')


# 生图服务的路由 ————————————————————————————————————————————————————————————————————————————————————————————————————————
@app.route('/generate', methods=['POST'])
def index():
    # 从 【post】请求中获取 【2 张图片】
    image_file_1 = request.files.get('image1') # 获取第一张图片的二进制流
    image_file_2 = request.files.get('image2') # 获取第二张图片的二进制流
    
    if not image_file_1 or not image_file_2:
        return jsonify({"error": "❌ 缺失 2 张图片"}), 400
    else: # 返回数据
        # 读取图片文件
        image_data_1 = request.files.get('image1')
        image_data_2 = request.files.get('image2')
        # image_data_1 = image_file_1.read()
        # image_data_2 = image_file_2.read()
        print("✅ 解码图片成功", image_file_1, image_file_2)
        print("————————————————————————————————————————————————")
        
        filename_1 = 'uploaded_image_1.jpg'
        filename_2 = 'uploaded_image_2.jpg'
        filepath_1 = os.path.join(app.config['UPLOAD_FOLDER'], filename_1)
        filepath_2 = os.path.join(app.config['UPLOAD_FOLDER'], filename_2)
        image_data_1.save(filepath_1) # 保存图片
        image_data_2.save(filepath_2) # 保存图片
        print("✅ 保存图片成功", filepath_1, filepath_2)
        # 将图片数据转换为二进制字符串, latin-1 表示每个字符占用一个字节
        # image_string_1 = image_data_1.decode('latin-1')
        # image_string_2 = image_data_2.decode('latin-1')
        
        # 将图片转为 base64 编码的格式
        # image_base64_1 = encode_image_to_base64(image_data_1)
        # image_base64_2 = encode_image_to_base64(image_data_2)
        
        # 打开 json 工作流
        # 获取当前文件所在的目录（即main.py所在的目录）
        current_directory = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_directory, 'prompt', 'flow.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            json_flow_text = f.read()
            
            # 🌟 修改 prompt 字典中的图片数据
            prompt_dict = json.loads(json_flow_text)
            
            # 修改 json 数据
            prompt_dict["139"]["inputs"]["image1"] = filepath_1 # 修改第一张图片
            prompt_dict["144"]["inputs"]["image2"] = filepath_2 # 修改第二张图片
            
        

		    # 文生图 - 【发送生图请求】 ————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————        
            # 发送请求, 开始进入队列进行生图, 接口会返回一个生图队列的 id
            response = requests.post(url=f'{url}/prompt', json={"prompt": prompt_dict}) # 把提示词替换为传入的 flow.json
            # 确保响应状态码为200（成功）
            if response.status_code == 200:
                response_jsonData = response.json() # 不会马上响应, 只会返回个队列 ID , 如果有 id 了则是生成好了图片
        
                #  获得下发的生图任务 id
                time.sleep(5)
                # 检查 response_jsonData 是否包含'prompt_id'
                if "prompt_id" in response_jsonData:
                    prompt_id = response_jsonData["prompt_id"]
                    print("✅ 返回了任务 id: ", prompt_id)

  		        # 查看下 output
                if prompt_id:
                    try:
                        # 【获得生图结果】 
                        res = ''
                        res = check_image_status(prompt_id)
                        res_data = res.get_json() # 在 Flask 中, 当使用 jsonify() 创建一个响应时，实际上是返回了一个 Flask Response 对象, 其中包含了 JSON 格式的字符串作为其数据。要访问这个数据, 需要先检查响应的状态码, 然后解析响应内容为 JSON
                        print("✅ 拿到了生图结果: ", res_data)
                
                        img_name = res_data["9"]['images'][0]['filename']
                        
                        # 🔥 使用view 接口来获取图片信息 ————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
                        view_image_path = f'{url}/view?filename={img_name}' 
                        print("✅  拿到了图片路径: ", view_image_path)
                        return view_image_path
    
                    except Exception as e:
                        return jsonify({"❌ Error": str(e)}), 500
                else:
                    return jsonify({"❌ Error": "生图失败"}), 500
                

# 初始化 __main__
if __name__ == "__main__":
	app.run(port=5000, debug=True)


