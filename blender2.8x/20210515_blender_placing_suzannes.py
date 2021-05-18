import math
import random
from typing import List, Tuple

import bpy
from bpy.types import Collection, Object, Scene
from mathutils.bvhtree import BVHTree

"""
ベースオブジェクトを複製回数分コピーしてランダムに配置するblender2.8x用コードです。
リジッドボディ設定もします。

重なり検出して、重なっている場所には配置されませんが
座標はランダムで取得するので、1オブジェクトあたり最大試行回数分配置してみて
だめだったら諦めて次のオブジェクトを配置しようとします。
"""

# 定数
BASE_OBJ_NAME = 'base_obj'  # ベースオブジェクト名
COPIES = 100  # 複製回数
PLACING_AREA_RANGE = [5, 5, 10]  # コピーしたオブジェクトを配置する範囲
Z_OFFSET = 2  # コピーしたオブジェクトを配置する範囲のうち、Z座標の最低値
COLLECTION_OF_COPIED = 'copied'  # コピーしたオブジェクトの格納用コレクション名
MAX_TRYIALS = 10  # 1複製オブジェクトのランダム配置の最大試行回数


def crear_collection(collection_name: str, scene: Scene) -> Collection:
    """
    コレクション作る(既存の場合、クリア上書き)
    """
    collection = bpy.data.collections.get(collection_name)

    # すでに同名のコレクションが存在する場合は消す
    if collection:
        # コレクション内のオブジェクト消す 他から参照されてようが消す
        objs_in_collection = [o for o in collection.objects]
        while objs_in_collection:
            bpy.data.objects.remove(objs_in_collection.pop())

        # コレクション自体も消す
        bpy.data.collections.remove(collection)

    # コレクション作る
    collection = bpy.data.collections.new(collection_name)
    scene.collection.children.link(collection)
    return collection


def get_random_location(max: Tuple[float, float, float], z_offset: float = 0.0) -> Tuple[float, float, float]:
    """
    ランダム座標取得
    """
    x_val = (random.random() - 0.5) * max[0] * 2
    y_val = (random.random() - 0.5) * max[1] * 2
    z_val = random.random() * (max[2] - z_offset) + z_offset
    return (x_val, y_val, z_val)


def get_random_rotation() -> List[float]:
    """
    ランダム回転取得
    """
    x_val = (random.random() - 0.5) * 4 * math.pi
    y_val = (random.random() - 0.5) * 4 * math.pi
    z_val = (random.random() - 0.5) * 4 * math.pi
    return [x_val, y_val, z_val]


def is_overlap_two(obj1: Object, obj2: Object) -> bool:
    """
    2オブジェクトが重なってないかチェックする
    毎回BVHTree作ってるのはどう考えても効率悪いけど
    死ぬほど遅くなければこのままでいい…
    参考：https://blender.stackexchange.com/questions/149891/python-in-blender-2-8-testing-if-two-objects-overlap-in-the-xy-plane/150014
    """
    # Get their world matrix
    mat1 = obj1.matrix_world
    mat2 = obj2.matrix_world

    # Get the geometry in world coordinates
    vert1 = [mat1 @ v.co for v in obj1.data.vertices]
    poly1 = [p.vertices for p in obj1.data.polygons]

    vert2 = [mat2 @ v.co for v in obj2.data.vertices]
    poly2 = [p.vertices for p in obj2.data.polygons]

    # Create the BVH trees
    bvh1 = BVHTree.FromPolygons(vert1, poly1)
    bvh2 = BVHTree.FromPolygons(vert2, poly2)

    # -> bool:にしておけばboolにcastされるのか？よくわからないのでTrueFalseで返す
    if bvh1.overlap(bvh2):
        return True
    else:
        return False


def is_overlap_list(obj: Object, compare_objs: Tuple[Object, ...]) -> bool:
    """
    あるオブジェクトと、タプル中のオブジェクトが重なってないかチェックする
    """
    result = False

    for compare_obj in compare_objs:
        if obj.name == compare_obj.name:
            continue

        if is_overlap_two(obj, compare_obj):
            result = True
            break
    return result


def main():
    """
    メイン処理
    """
    # 既存の情報取得する
    base_obj: Object = bpy.data.objects.get(BASE_OBJ_NAME)
    scene: Scene = bpy.context.scene

    # 複製オブジェクト格納用コレクション準備
    copied_collection = crear_collection(COLLECTION_OF_COPIED, scene)

    # コピーしてランダムに配置
    for i in range(0, COPIES):
        copied_obj: Object = base_obj.copy()
        copied_obj.name = f"copied_{i:03d}"

        trial = 1

        # ランダム座標＆回転で配置してみて、重なってなければ採用（break）
        while trial <= MAX_TRYIALS:
            copied_obj.location = get_random_location(
                PLACING_AREA_RANGE, Z_OFFSET)
            copied_obj.rotation_euler = get_random_rotation()
            copied_collection.objects.link(copied_obj)  # 絶対このあたり遅くなってる
            bpy.context.view_layer.update()  # 強制再描画…
            if not is_overlap_list(copied_obj, copied_collection.all_objects):
                break
            copied_collection.objects.unlink(copied_obj)
            trial += 1

        # だめなときは諦める
        if trial > MAX_TRYIALS:
            print(f"置けなかったので諦めた {i:03d}個目 試行回数:{trial - 1}")
            bpy.data.objects.remove(copied_obj)

    # リジッドボディを複製オブジェクトに1つ1つ追加
    for rigid_obj in copied_collection.all_objects:
        rigid_obj.select_set(True)  # 画面上でやるのと同じ操作なのが気に入らない…
        bpy.context.view_layer.objects.active = rigid_obj
        bpy.ops.rigidbody.objects_add()
        rigid_obj.select_set(False)

    print(f"{len(copied_collection.objects)}個置けた")


if __name__ == "__main__":
    main()
