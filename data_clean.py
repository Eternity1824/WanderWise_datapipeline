import json
import requests
from openai import OpenAI


class GeocodeFinder:
    """使用 Google Maps Geocoding API 查找坐标"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def get_coordinates(self, place_name, region="us", language="en"):
        """通过地点名称查询坐标，返回结果列表"""
        # 构建参数
        params = {
            "address": place_name,
            "key": self.api_key,
            "language": language,
            "region": region
        }

        # 发送请求
        response = requests.get(self.base_url, params=params)

        # 解析响应
        result = response.json()

        locations = []

        if result["status"] == "OK":
            for location in result['results']:
                lat = location['geometry']['location']['lat']
                lng = location['geometry']['location']['lng']

                loc_data = {
                    "formatted_address": location['formatted_address'],
                    "lat": lat,
                    "lng": lng,
                    "place_id": location['place_id'],
                    "location_type": location['geometry']['location_type']
                }
                if location['geometry']['location_type'] == "ROOFTOP":
                    locations.append(loc_data)

        return locations


def extract_locations_with_deepseek(post):
    """使用DeepSeek API从post中提取可能的地理位置"""
    client = OpenAI(api_key="sk-95981642162246b78a24497688378291", base_url="https://api.deepseek.com")
    prompt = f"""
    请从以下小红书帖子中提取所有可能的地理位置（精确到餐馆名或者景点名）（餐厅、景点等名称和地址）。
    重要: 提取的每个地点名称必须包含来源关键词中的城市名称作为后缀，例如"洞庭春, Seattle"而不是仅"洞庭春"。
    仅返回JSON格式的地点列表，不要有任何其他文字。如果没有找到就返回空的列表即可。
    格式: ["洞庭春, Seattle", ...]

    帖子标题: {post['title']}
    帖子内容: {post['desc']}
    标签: {post.get('tag_list', '')}
    来源关键词: {post.get('source_keyword', '')}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的地理位置提取助手，只输出JSON格式结果"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        locations_text = response.choices[0].message.content

        # 尝试解析返回的JSON
        try:
            import re
            # 查找方括号内的JSON数组
            json_match = re.search(r'\[.*\]', locations_text, re.DOTALL)
            if json_match:
                locations_json = json.loads(json_match.group(0))
                return locations_json
            else:
                print(f"无法在结果中找到JSON: {locations_text}")
                return []
        except json.JSONDecodeError:
            print(f"JSON解析失败: {locations_text}")
            return []

    except Exception as e:
        print(f"DeepSeek API调用失败: {str(e)}")
        return []


def rate_post(post, locations):
    """使用DeepSeek API对post进行打分"""
    client = OpenAI(api_key="sk-95981642162246b78a24497688378291", base_url="https://api.deepseek.com")

    # 处理locations信息，避免格式化错误
    locations_addresses = []
    locations_coords = []

    for loc in locations:
        try:
            locations_addresses.append(str(loc['formatted_address']))
            locations_coords.append(f"{loc['lat']}, {loc['lng']}")
        except (KeyError, TypeError) as e:
            print(f"处理location信息时出错: {e}, location: {loc}")

    # 准备评分提示
    prompt = f"""
    请对这篇美食或旅游点评进行打分（满分100分），评分标准如下：
    1. 内容质量（30分）：描述详细程度、是否有实用信息
    2. 真实性（20分）：是否有实际体验的描述细节
    3. 有用程度（20分）：对其他用户的参考价值
    4. 受欢迎度（30分）：根据用户互动数据评估

    点评信息：
    标题: {post['title']}
    内容: {post['desc']}
    地点: {', '.join(locations_addresses)}
    坐标: {', '.join(locations_coords)}

    用户互动数据：
    点赞数: {post.get('liked_count', '0')}
    收藏数: {post.get('collected_count', '0')}
    评论数: {post.get('comment_count', '0')}
    分享数: {post.get('share_count', '0')}

    格式为JSON:
    {{"score": 分数}}
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的美食和旅游内容评分助手，只输出JSON格式结果"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        score_result = response.choices[0].message.content

        # 尝试解析返回的JSON
        try:
            import re
            # 查找花括号内的JSON对象
            json_match = re.search(r'\{.*\}', score_result, re.DOTALL)
            if json_match:
                score_json = json.loads(json_match.group(0))
                return score_json
            else:
                return {"score": 70}
        except json.JSONDecodeError:
            return {"score": 70}

    except Exception as e:
        print(f"评分API调用失败: {str(e)}")
        return {"score": 60}


def process_posts(posts_data, google_api_key, save_interval=50):
    """处理所有posts，每50条保存一次"""
    geocoder = GeocodeFinder(google_api_key)
    valid_posts = []
    i = 0

    for post in posts_data:
        print(f"正在处理第{i + 1}条post,post id: {post['note_id']}")
        # 使用DeepSeek提取地理位置
        potential_locations = extract_locations_with_deepseek(post)
        print(f"可能的地点{potential_locations}")
        all_coordinates = []
        # 对每个潜在地点查询坐标
        for location in potential_locations:
            coordinates = geocoder.get_coordinates(location)
            all_coordinates.extend(coordinates)

        # 如果找到了地理位置，则保留这个post
        if all_coordinates:
            # 使用DeepSeek对post进行评分
            score_info = rate_post(post, all_coordinates)

            # 将地理位置和评分信息添加到post中
            enriched_post = post.copy()
            enriched_post["locations"] = all_coordinates
            enriched_post["score"] = score_info.get("score", 0)

            valid_posts.append(enriched_post)

        i += 1

        # 每处理save_interval条帖子保存一次
        if i % save_interval == 0:
            try:
                with open(f'processed_search_contents_2025-03-11_part_{i // save_interval}.json', 'w',
                          encoding='utf-8') as f:
                    json.dump(valid_posts, f, ensure_ascii=False, indent=2)
                print(f"已处理 {i} 条帖子，找到 {len(valid_posts)} 个有效posts，已保存中间结果")
            except Exception as e:
                print(f"保存中间数据失败: {str(e)}")

    return valid_posts


def main():
    # 从文件加载posts数据
    try:
        with open('search_contents_2025-03-11.json', 'r', encoding='utf-8') as f:
            posts_data = json.load(f)
    except Exception as e:
        print(f"加载数据失败: {str(e)}")
        posts_data = []  # 或使用示例数据

    # 使用你的Google Maps API key
    google_api_key = "AIzaSyD4K_0sPAIWmIE8jandYAlaNqMSTu9jAOY"

    # 处理posts，每50条保存一次
    valid_posts = process_posts(posts_data, google_api_key, save_interval=50)

    # 保存最终处理后的完整数据
    try:
        with open('processed_search_contents_2025-03-11_final.json', 'w', encoding='utf-8') as f:
            json.dump(valid_posts, f, ensure_ascii=False, indent=2)
        print(f"成功处理 {len(valid_posts)} 个有效posts，已保存到 processed_search_contents_2025-03-11_final.json")
    except Exception as e:
        print(f"保存最终数据失败: {str(e)}")


if __name__ == "__main__":
    main()