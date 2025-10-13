# effects/particle_system.py
"""パーティクルエフェクトシステム"""

import random
import pyxel


class Particle:
    """単一のパーティクル"""
    
    def __init__(self, x, y):
        """
        パーティクルを初期化
        
        Args:
            x: 初期X座標
            y: 初期Y座標
        """
        self.x = x
        self.y = y
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-2.5, 0.5)
        self.life = random.randint(20, 40)
        self.color = random.choice([7, 8, 9, 10, 11, 12, 13])

    def update(self):
        """パーティクルの位置と状態を更新"""
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12  # 重力
        self.life -= 1

    def draw(self):
        """パーティクルを描画"""
        pyxel.pset(self.x, self.y, self.color)

    def is_alive(self) -> bool:
        """パーティクルが生存しているか"""
        return self.life > 0


class ParticleSystem:
    """パーティクルシステム管理クラス"""
    
    def __init__(self):
        """パーティクルシステムを初期化"""
        self.particles = []

    def add_explosion(self, x, y, count=40):
        """
        爆発エフェクトを追加
        
        Args:
            x: 爆発の中心X座標
            y: 爆発の中心Y座標
            count: 生成するパーティクル数
        """
        for _ in range(count):
            self.particles.append(Particle(x, y))

    def add_particle(self, particle):
        """
        単一のパーティクルを追加
        
        Args:
            particle: Particleインスタンス
        """
        self.particles.append(particle)

    def update_all(self):
        """全パーティクルを更新し、死んだパーティクルを削除"""
        for particle in self.particles:
            particle.update()
        
        # 生存しているパーティクルのみ保持
        self.particles = [p for p in self.particles if p.is_alive()]

    def draw_all(self):
        """全パーティクルを描画"""
        for particle in self.particles:
            particle.draw()

    def clear(self):
        """全パーティクルをクリア"""
        self.particles.clear()

    def get_count(self) -> int:
        """現在のパーティクル数を取得"""
        return len(self.particles)

    def slow_down(self, factor=0.95):
        """
        全パーティクルの速度を減衰させる（ホワイトアウト演出用）
        
        Args:
            factor: 速度の減衰率（0.0-1.0）
        """
        for particle in self.particles:
            particle.vx *= factor
            particle.vy *= factor