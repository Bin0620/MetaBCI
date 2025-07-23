import sys
import os
import time

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, welch
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QWidget, QStackedWidget,
                             QFileDialog, QLineEdit, QMessageBox, QSpinBox, QGroupBox)
from PyQt5.QtChart import QChart, QChartView, QLineSeries

# 导入我们封装的NeuroPy类
from metabci.brainflow.amplifiers import NeuroPy
from metabci.brainda.algorithms.feature_analysis.adhd import ADHDDiagnosisModel
from metabci.brainda.algorithms.feature_analysis.freq_analysis import FrequencyAnalysis


# 睁闭眼范式界面
class EyePatternWidget(QWidget):
    """睁闭眼范式界面"""

    def __init__(self):
        super().__init__()
        self.initUI()
        self.open_eye = True
        self.pattern_running = False
        self.current_tag = 1
        self.cycle_count = 0
        self.max_cycles = 5
        self.eye_timer = QTimer(self)
        self.eye_timer.timeout.connect(self.toggle_eye_state)
        self.eye_duration = 15000  # 每个状态持续15秒
        self.timestamps = []

    def initUI(self):
        self.setWindowTitle('睁闭眼范式')
        self.setGeometry(500, 50, 1000, 800)
        self.cycles_layout = QHBoxLayout()
        self.cycles_label = QLabel("设置睁闭眼次数:")
        self.cycles_spin = QSpinBox()
        self.cycles_spin.setRange(1, 20)
        self.cycles_spin.setValue(5)
        self.cycles_spin.valueChanged.connect(self.set_max_cycles)
        self.cycles_layout.addWidget(self.cycles_label)
        self.cycles_layout.addWidget(self.cycles_spin)
        self.status_label = QLabel("准备开始")
        self.status_label.setFont(QFont("Arial", 16))
        self.cycles_completed_label = QLabel("已完成: 0/5 次")
        self.cycles_completed_label.setFont(QFont("Arial", 14))
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.cycles_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.cycles_completed_label)
        main_layout.addStretch()
        self.setLayout(main_layout)

    def set_max_cycles(self, value):
        self.max_cycles = value
        self.cycles_completed_label.setText(f"已完成: {self.cycle_count}/{self.max_cycles} 次")

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pattern_running:
            painter.fillRect(self.rect(), QColor(255, 255, 255))
        else:
            painter.fillRect(self.rect(), QColor(128, 128, 128))
            if self.open_eye:
                pen = QPen(Qt.black, 40)
                painter.setPen(pen)
                margin = 0.3
                x_margin = int(self.width() * margin)
                y_margin = int(self.height() * margin)
                cross_x = self.width() // 2
                cross_y = self.height() // 2
                painter.drawLine(x_margin, cross_y, self.width() - x_margin, cross_y)
                painter.drawLine(cross_x, y_margin, cross_x, self.height() - y_margin)

    def toggle_eye_state(self):
        self.open_eye = not self.open_eye
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        state = "睁眼" if self.open_eye else "闭眼"
        self.timestamps.append((timestamp, state, self.current_tag))
        print(f"时间: {timestamp}, 状态: {state}, 标签: {self.current_tag}")
        self.update()
        if self.open_eye:
            self.cycle_count += 1
            self.current_tag = 1
            self.cycles_completed_label.setText(f"已完成: {self.cycle_count}/{self.max_cycles} 次")
            self.status_label.setText("睁眼阶段")
            if self.cycle_count >= self.max_cycles:
                self.stop_pattern()
        else:
            self.current_tag = 2
            self.status_label.setText("闭眼阶段")

    def start_pattern(self):
        if not self.pattern_running:
            self.pattern_running = True
            self.open_eye = True
            self.cycle_count = 0
            self.timestamps = []
            self.cycles_completed_label.setText(f"已完成: {self.cycle_count}/{self.max_cycles} 次")
            self.status_label.setText("睁眼阶段")
            self.current_tag = 1
            self.timestamps.append((
                QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz"),
                "睁眼",
                self.current_tag
            ))
            self.eye_timer.start(self.eye_duration)
            self.update()

    def stop_pattern(self):
        self.eye_timer.stop()
        self.pattern_running = False
        self.status_label.setText("实验完成")
        self.update()
        self.save_timestamps()

    def save_timestamps(self):
        try:
            df = pd.DataFrame(self.timestamps, columns=['时间戳', '状态', '标签'])
            main_window = self.parent()
            while main_window and not isinstance(main_window, MainWindow):
                main_window = main_window.parent()
            if main_window and hasattr(main_window, 'real_time_data'):
                save_dir = main_window.real_time_data.save_directory
                filename = main_window.real_time_data.filename
                if save_dir and filename:
                    filepath = f"{save_dir}/{filename}_tags.csv"
                    df.to_csv(filepath, index=False)
                    print(f"标签数据已保存至: {filepath}")
        except Exception as e:
            print(f"保存标签数据失败: {e}")
            QMessageBox.warning(self, "保存失败", f"标签数据保存失败: {str(e)}")


# 实时数据界面
class RealTimeData(QWidget):
    def __init__(self, parent=None, max_time=6):
        super().__init__(parent)
        self.max_time = max_time
        self.current_time = 0

        # 初始化NeuroPy设备
        self.neuropy = NeuroPy(
            port="COM4",  # 根据实际设备修改
            baud_rate=57600
        )

        # 修改ADHD模型初始化
        self.adhd_model = ADHDDiagnosisModel()
        self.last_diagnosis_time = 0

        # 初始化频域分析工具
        self.freq_analyzer = None
        self.fs = 512  # 采样率
        self._initialize_freq_analyzer()  # 初始化频率分析工具

        # 设置回调函数
        self.neuropy.set_callback('raw_value', self.update_raw_value)
        self.neuropy.set_callback('attention', self.update_attention)
        self.neuropy.set_callback('delta', self.update_delta)
        self.neuropy.set_callback('theta', self.update_theta)
        self.neuropy.set_callback('low_beta', self.update_low_beta)
        self.neuropy.set_callback('high_beta', self.update_high_beta)

        self.initUI()
        self.setup_data_handling()

    def _initialize_freq_analyzer(self):
        """初始化频率分析工具"""
        try:
            import pandas as pd
            # 创建伪数据用于初始化FrequencyAnalysis
            dummy_data = np.zeros((1, 1, 100))  # 1 trial, 1 channel, 100 samples
            dummy_meta = pd.DataFrame({"event": ["dummy"]}, index=[0])

            self.freq_analyzer = FrequencyAnalysis(
                data=dummy_data,
                meta=dummy_meta,
                event="dummy",
                srate=self.fs
            )
        except Exception as e:
            print(f"初始化FrequencyAnalysis失败: {e}")
            self.freq_analyzer = None

    def initUI(self):
        """界面初始化"""
        self.layout = QVBoxLayout(self)
        self.create_charts()

        # 数据标签布局
        labels_layout = QHBoxLayout()
        self.raw_label = QLabel("原始值: 0")
        self.attention_label = QLabel("专注度: 0")
        self.ratio_label = QLabel("β/θ: 0.00")
        for label in [self.raw_label, self.attention_label, self.ratio_label]:
            label.setFont(QFont("Arial", 14))
            labels_layout.addWidget(label)
        self.layout.addLayout(labels_layout)

        # 文件保存设置
        self.setup_file_saving()

        # 诊断结果显示
        self.diagnosis_group = QGroupBox("ADHD诊断结果")
        self.diagnosis_layout = QVBoxLayout()
        self.diagnosis_status = QLabel("等待足够数据进行诊断...")
        self.diagnosis_status.setFont(QFont("Arial", 16, QFont.Bold))
        self.diagnosis_status.setAlignment(Qt.AlignCenter)
        self.diagnosis_probability = QLabel("ADHD概率: N/A")
        self.diagnosis_probability.setFont(QFont("Arial", 14))
        self.diagnosis_probability.setAlignment(Qt.AlignCenter)
        self.features_label = QLabel("特征: N/A")
        self.features_label.setFont(QFont("Arial", 12))
        self.features_label.setAlignment(Qt.AlignLeft)
        self.diagnosis_layout.addWidget(self.diagnosis_status)
        self.diagnosis_layout.addWidget(self.diagnosis_probability)
        self.diagnosis_layout.addWidget(self.features_label)
        self.diagnosis_group.setLayout(self.diagnosis_layout)
        self.layout.addWidget(self.diagnosis_group)

    def create_charts(self):
        """创建图表"""
        # 原始信号图表
        self.series1 = QLineSeries()
        self.chart1 = QChart()
        self.chart1.addSeries(self.series1)
        self.chart1.createDefaultAxes()
        self.chart1.setTitle("原始信号")
        self.chart1.legend().hide()
        self.chart1.axisY().setRange(-500, 500)
        self.chartView1 = QChartView(self.chart1)
        self.chartView1.setRenderHint(QPainter.Antialiasing)
        self.layout.addWidget(self.chartView1)

        # 专注度图表
        self.series2 = QLineSeries()
        self.chart2 = QChart()
        self.chart2.addSeries(self.series2)
        self.chart2.createDefaultAxes()
        self.chart2.setTitle("专注度")
        self.chart2.legend().hide()
        self.chart2.axisY().setRange(0, 100)
        self.chartView2 = QChartView(self.chart2)
        self.chartView2.setRenderHint(QPainter.Antialiasing)
        self.layout.addWidget(self.chartView2)

        # β/θ比值图表
        self.series3 = QLineSeries()
        self.chart3 = QChart()
        self.chart3.addSeries(self.series3)
        self.chart3.createDefaultAxes()
        self.chart3.setTitle("β/θ比值")
        self.chart3.legend().hide()
        self.chart3.axisY().setRange(0, 10)
        self.chartView3 = QChartView(self.chart3)
        self.chartView3.setRenderHint(QPainter.Antialiasing)
        self.layout.addWidget(self.chartView3)

    def setup_data_handling(self):
        """数据存储和处理设置"""
        self.raw_data = []  # 原始脑电数据
        self.filtered_data = []  # 滤波后数据
        self.attention_data = []  # 注意力数据
        self.theta_data = []  # θ波数据
        self.low_beta_data = []  # 低β波数据
        self.high_beta_data = []  # 高β波数据
        self.ratio_data = []  # β/θ比值数据

        # 信号处理参数
        self.fs = 512  # 采样率(Hz)
        self.lowcut = 4  # θ波下限(Hz)
        self.highcut = 30  # β波上限(Hz)

        # 数据更新定时器
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.update_data)
        self.data_timer.start(50)  # 20Hz更新频率(每50ms)

        # 诊断定时器 - 每30秒进行一次诊断
        self.diagnosis_timer = QTimer(self)
        self.diagnosis_timer.timeout.connect(self.perform_diagnosis)
        self.diagnosis_timer.start(30000)

    def setup_file_saving(self):
        """文件保存设置"""
        self.save_directory = None
        self.filename = "eeg_data"
        file_layout = QHBoxLayout()
        self.folder_button = QPushButton("选择保存文件夹")
        self.folder_button.clicked.connect(self.select_directory)
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("输入文件名")
        self.filename_edit.textChanged.connect(self.update_filename)
        file_layout.addWidget(self.folder_button)
        file_layout.addWidget(self.filename_edit)
        self.layout.addLayout(file_layout)

    # 回调更新方法
    def update_raw_value(self, value):
        """更新原始值数据"""
        self.raw_data.append(value)
        self.raw_label.setText(f"原始值: {value}")

    def update_attention(self, value):
        """更新注意力数据"""
        self.attention_data.append(value)
        self.attention_label.setText(f"专注度: {value}")

    def update_delta(self, value):
        """更新δ波数据"""
        pass  # 当前不需要使用δ波数据

    def update_theta(self, value):
        """更新θ波数据"""
        self.theta_data.append(value)

    def update_low_beta(self, value):
        """更新低β波数据"""
        self.low_beta_data.append(value)

    def update_high_beta(self, value):
        """更新高β波数据"""
        self.high_beta_data.append(value)
        self.update_beta_theta_ratio()

    def update_beta_theta_ratio(self):
        """计算并更新β/θ比值"""
        try:
            if len(self.theta_data) > 0 and len(self.high_beta_data) > 0 and len(self.low_beta_data) > 0:
                # 取最近10个数据点的平均值以减少波动
                window_size = 10
                theta_avg = np.mean(self.theta_data[-window_size:]) if len(self.theta_data) >= window_size else np.mean(
                    self.theta_data)
                beta_avg = (np.mean(self.high_beta_data[-window_size:]) + np.mean(
                    self.low_beta_data[-window_size:])) / 2

                if theta_avg > 0:  # 避免除以零
                    ratio = beta_avg / theta_avg
                    self.ratio_data.append(ratio)
                    self.ratio_label.setText(f"β/θ: {ratio:.2f}")
        except Exception as e:
            print(f"计算β/θ比值时出错: {e}")

    def compute_psd(self, data, fs):
        """使用scipy的welch方法计算功率谱密度"""
        try:
            # 确保输入是numpy数组
            data = np.asarray(data)
            # 使用Welch方法计算PSD
            freqs, psd = welch(data, fs, nperseg=min(1024, len(data)))
            return freqs, psd
        except Exception as e:
            print(f"计算功率谱密度时出错: {e}")
            return None, None

    def update_data(self):
        try:
            if len(self.raw_data) > 100:
                # 使用副本避免线程冲突
                data_copy = np.array(self.raw_data[-100:])

                # 改用进程池避免界面卡顿
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor() as executor:
                    future = executor.submit(
                        self.freq_analyzer.butter_bandpass_filter,
                        data_copy, 4, 30, self.fs
                    )
                    filtered = future.result()

                self.filtered_data.extend(filtered)
        except Exception as e:
            print(f"滤波处理失败: {e}")

        # 更新时间和图表
        self.current_time += 50
        self.update_charts()

        # 当有足够数据时进行诊断
        if len(self.ratio_data) > 100:  # 大约5秒的数据
            # 每100个数据点进行一次快速诊断更新
            if len(self.ratio_data) % 100 == 0:
                self.perform_diagnosis()

    def update_charts(self):
        """更新图表显示"""
        max_points = int(self.max_time * 1000 / 50)  # 显示max_time秒的数据

        # 更新原始信号图表
        self.series1.clear()
        for i, val in enumerate(self.raw_data[-max_points:]):
            self.series1.append(i * 50, val)
        self.chart1.axisX().setRange(0, max_points * 50)

        # 更新专注度图表
        self.series2.clear()
        for i, val in enumerate(self.attention_data[-max_points:]):
            self.series2.append(i * 50, val)
        self.chart2.axisX().setRange(0, max_points * 50)

        # 更新β/θ比值图表
        self.series3.clear()
        for i, val in enumerate(self.ratio_data[-max_points:]):
            self.series3.append(i * 50, val)
        self.chart3.axisX().setRange(0, max_points * 50)

    def select_directory(self):
        """选择保存目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择保存文件夹")
        if directory:
            self.save_directory = directory

    def update_filename(self, text):
        """更新文件名"""
        self.filename = text.strip() or "eeg_data"

    def save_data(self):
        """保存数据"""
        if not self.save_directory:
            QMessageBox.warning(self, "保存失败", "请先选择保存文件夹")
            return

        try:
            # 确保数据长度一致
            min_length = min(
                len(self.raw_data),
                len(self.filtered_data),
                len(self.attention_data),
                len(self.ratio_data)
            )

            # 创建数据框
            data = {
                "timestamp": [i * 50 for i in range(min_length)],
                "raw": self.raw_data[:min_length],
                "filtered": self.filtered_data[:min_length],
                "attention": self.attention_data[:min_length],
                "beta_theta_ratio": self.ratio_data[:min_length]
            }

            df = pd.DataFrame(data)

            # 保存数据
            filepath = os.path.join(self.save_directory, f"{self.filename}.csv")
            df.to_csv(filepath, index=False)
            print(f"数据已保存到: {filepath}")

            QMessageBox.information(self, "保存成功", f"数据已成功保存到:\n{filepath}")

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存数据时出错:\n{str(e)}")

    def closeEvent(self, event):
        """窗口关闭时停止采集"""
        if hasattr(self.neuropy, 'stop'):
            self.neuropy.stop()  # 停止NeuroPy数据采集
        event.accept()

    def update_diagnosis_display(self, result):
        """更新诊断结果显示（优化版）"""
        try:
            probability = float(result.get('probability', 0))
            diagnosis = str(result.get('diagnosis', "未知状态"))
            features = result.get('features', {})

            # 设置颜色和诊断结论
            diagnosis_text = f"诊断结论: {diagnosis}"
            if probability < 0.3:
                color = "green"
                diagnosis_text += " (正常范围)"
            elif probability < 0.7:
                color = "orange"
                diagnosis_text += " (建议复查)"
            else:
                color = "red"
                diagnosis_text += " (建议就医)"

            self.diagnosis_status.setText(diagnosis_text)
            self.diagnosis_status.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 14px;"
            )

            # 显示概率和特征
            self.diagnosis_probability.setText(
                f"ADHD风险概率: {probability * 100:.1f}%"
            )

            # 特征显示带参考值
            feature_ref = self.adhd_model.get_feature_reference_ranges()
            feature_text = (
                f"β/θ比值: {features.get('beta_theta_ratio', 0):.2f} ({feature_ref['beta_theta_ratio']})\n"
                f"平均注意力: {features.get('attention_mean', 0):.1f} ({feature_ref['attention_mean']})\n"
                f"注意力波动: {features.get('attention_std', 0):.1f} ({feature_ref['attention_std']})"
            )
            self.features_label.setText(feature_text)

        except Exception as e:
            print(f"更新诊断显示时出错: {e}")
            self.diagnosis_status.setText("诊断结果显示错误")

    def perform_diagnosis(self):
        """执行ADHD诊断（与模型匹配的版本）"""
        try:
            # 检查是否有足够数据
            min_data_points = 100
            if len(self.ratio_data) < min_data_points or len(self.attention_data) < min_data_points:
                self.diagnosis_status.setText(f"数据收集中... (需要{min_data_points}个数据点)")
                return

            # 准备模型输入数据（最近100个点）
            beta_theta_window = self.ratio_data[-min_data_points:]
            attention_window = self.attention_data[-min_data_points:]

            # 调用模型预测（两种方式适配）
            try:
                # 方式1：直接传递参数
                result = self.adhd_model.predict(
                    beta_theta_ratios=beta_theta_window,
                    attention_values=attention_window
                )
            except TypeError:
                # 方式2：如果模型需要字典参数
                result = self.adhd_model.predict({
                    'beta_theta_ratios': beta_theta_window,
                    'attention_values': attention_window
                })

            # 更新UI显示
            self.update_diagnosis_display(result)

            # 记录最后诊断时间
            self.last_diagnosis_time = time.time()

        except Exception as e:
            error_msg = f"诊断错误: {str(e)}"
            print(error_msg)
            self.diagnosis_status.setText(error_msg)


# 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('脑电信号分析系统')
        self.setGeometry(100, 100, 1200, 800)

        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 添加界面
        self.eye_pattern = EyePatternWidget()
        self.real_time_data = RealTimeData()

        self.stacked_widget.addWidget(self.eye_pattern)
        self.stacked_widget.addWidget(self.real_time_data)

        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # 控制按钮
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始实验")
        self.stop_btn = QPushButton("停止实验")
        self.save_btn = QPushButton("保存数据")

        self.start_btn.clicked.connect(self.start_experiment)
        self.stop_btn.clicked.connect(self.stop_experiment)
        self.save_btn.clicked.connect(self.save_data)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.save_btn)

        # 界面切换按钮
        switch_layout = QHBoxLayout()

        self.eye_btn = QPushButton("范式界面")
        self.data_btn = QPushButton("数据界面")

        self.eye_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.data_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        switch_layout.addWidget(self.eye_btn)
        switch_layout.addWidget(self.data_btn)

        # 添加到主布局
        main_layout.addLayout(switch_layout)
        main_layout.addWidget(self.stacked_widget)
        main_layout.addLayout(control_layout)

        self.setCentralWidget(main_widget)

    def start_experiment(self):
        """开始实验"""
        self.eye_pattern.start_pattern()
        # 启动NeuroPy设备
        try:
            self.real_time_data.neuropy.start()
            QMessageBox.information(self, "启动成功", "设备已成功启动")
        except Exception as e:
            QMessageBox.warning(self, "启动失败", f"无法启动设备: {str(e)}\n请检查设备连接")

        if hasattr(self.real_time_data, 'data_timer'):
            self.real_time_data.data_timer.start()

    def stop_experiment(self):
        """停止实验"""
        self.eye_pattern.stop_pattern()
        if hasattr(self.real_time_data, 'data_timer'):
            self.real_time_data.data_timer.stop()
        # 停止NeuroPy设备
        if hasattr(self.real_time_data.neuropy, 'stop'):
            self.real_time_data.neuropy.stop()
            QMessageBox.information(self, "已停止", "实验已停止")

    def save_data(self):
        """保存数据"""
        if hasattr(self.real_time_data, 'save_data'):
            self.real_time_data.save_data()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 检查依赖库
    try:
        import numpy as np
        from scipy.signal import butter, filtfilt, welch
        import pandas as pd
        import joblib
    except ImportError as e:
        QMessageBox.critical(None, "缺少依赖", f"请安装必要的Python库: {str(e)}")
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
