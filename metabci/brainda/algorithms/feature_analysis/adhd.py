import numpy as np
import joblib
from typing import Dict, Optional, Union


class ADHDDiagnosisModel:
    """
    ADHD诊断模型

    功能：
    - 基于EEG特征进行ADHD诊断评估
    - 支持预训练模型加载和基于规则的诊断

    特征：
    - beta_theta_ratio: β/θ波能量比值
    - attention_mean: 注意力平均值
    - attention_std: 注意力标准差

    使用示例：
    >>> model = ADHDDiagnosisModel("model_path.pkl")
    >>> result = model.predict(beta_theta_ratios, attention_values)
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        初始化ADHD诊断模型

        参数：
            model_path: 预训练模型路径(.pkl文件)，可选
        """
        self.model = None
        self.model_path = model_path
        self.is_loaded = False

        # 默认特征权重（基于文献的启发式规则）
        self.feature_weights = {
            'beta_theta_ratio': 0.1,  # β/θ比值权重
            'attention_mean': 0.6,  # 注意力均值权重
            'attention_std': 0.3  # 注意力波动权重
        }

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> None:
        """
        加载预训练模型

        参数：
            model_path: 模型文件路径(.pkl)
        """
        try:
            self.model = joblib.load(model_path)
            self.is_loaded = True
            print(f"成功加载模型: {model_path}")
        except Exception as e:
            print(f"模型加载失败: {e}")
            self.model = None
            self.is_loaded = False

    def extract_features(
            self,
            beta_theta_ratios: Union[list, np.ndarray],
            attention_values: Union[list, np.ndarray]
    ) -> Optional[Dict[str, float]]:
        """
        提取诊断特征

        参数：
            beta_theta_ratios: β/θ比值序列
            attention_values: 注意力值序列

        返回：
            特征字典（包含三个关键特征）或None（输入无效时）
        """
        if not beta_theta_ratios or not attention_values:
            return None

        return {
            'beta_theta_ratio': np.mean(beta_theta_ratios),
            'attention_mean': np.mean(attention_values),
            'attention_std': np.std(attention_values)
        }

    def predict(
            self,
            beta_theta_ratios: Union[list, np.ndarray],
            attention_values: Union[list, np.ndarray]
    ) -> Dict[str, Union[float, str, Dict]]:
        """
        执行ADHD诊断预测

        参数：
            beta_theta_ratios: β/θ比值序列
            attention_values: 注意力值序列

        返回：
            包含三个键的字典：
            - probability: ADHD概率(0-1)
            - diagnosis: 诊断结论文本
            - features: 使用的特征值
        """
        features = self.extract_features(beta_theta_ratios, attention_values)
        if features is None:
            return {
                'probability': 0.0,
                'diagnosis': '数据不足，无法诊断',
                'features': {}
            }

        # 使用机器学习模型或启发式规则
        if self.is_loaded and self.model:
            input_features = np.array([
                features['beta_theta_ratio'],
                features['attention_mean'],
                features['attention_std']
            ]).reshape(1, -1)
            probability = self.model.predict_proba(input_features)[0][1]
        else:
            # 基于规则的诊断
            probability = (
                    features['beta_theta_ratio'] * self.feature_weights['beta_theta_ratio'] +
                    (100 - features['attention_mean']) * self.feature_weights['attention_mean'] / 100 +
                    features['attention_std'] * self.feature_weights['attention_std'] / 10
            )
            probability = min(1.0, max(0.0, probability))  # 限制在0-1范围

        # 生成诊断结论
        if probability < 0.3:
            diagnosis = '正常（ADHD可能性低）'
        elif probability < 0.7:
            diagnosis = '可疑（建议进一步评估）'
        else:
            diagnosis = '高度疑似（建议专业医学诊断）'

        return {
            'probability': probability,
            'diagnosis': diagnosis,
            'features': features
        }

    def get_feature_reference_ranges(self) -> Dict[str, str]:
        """
        获取特征参考范围说明

        返回：
            各特征的正常参考范围说明
        """
        return {
            'beta_theta_ratio': '1.0-2.5 (正常范围)',
            'attention_mean': '50-80 (正常范围)',
            'attention_std': '5-15 (正常范围)'
        }