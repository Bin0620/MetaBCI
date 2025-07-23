from scipy.fftpack import fft
from scipy import signal
import numpy as np
import matplotlib.pyplot as plt
import mne
from scipy.signal import butter, filtfilt


class FrequencyAnalysis:
    def __init__(self, data, meta, event, srate, latency=0, channel="all"):
        """
        EEG频域分析工具类（增强版）

        Args:
            data: EEG数据 (nTrials, nChannels, nTimes)
            meta: 包含试验信息的DataFrame
            event: 需要分析的事件标记
            srate: 采样率(Hz)
            latency: 实验起始时间点(s)
            channel: 通道选择('all'或指定通道)
        """
        sub_meta = meta[meta["event"] == event]
        event_id = sub_meta.index.to_numpy()
        self.data_length = np.round(data.shape[2] / srate)
        if channel == "all":
            self.data = data[event_id, :, :]
        else:
            self.data = data[event_id, channel, :]
        self.latency = latency
        self.fs = srate

    @staticmethod
    def butter_bandpass(lowcut, highcut, fs, order=4):
        """
        生成巴特沃斯带通滤波器系数

        Args:
            lowcut: 低频截止(Hz)
            highcut: 高频截止(Hz)
            fs: 采样率(Hz)
            order: 滤波器阶数

        Returns:
            b, a: 滤波器系数
        """
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        return b, a

    @staticmethod
    def butter_bandpass_filter(data, lowcut, highcut, fs, order=4):
        """
        应用巴特沃斯带通滤波

        Args:
            data: 输入信号
            lowcut: 低频截止(Hz)
            highcut: 高频截止(Hz)
            fs: 采样率(Hz)
            order: 滤波器阶数

        Returns:
            y: 滤波后信号
        """
        b, a = FrequencyAnalysis.butter_bandpass(lowcut, highcut, fs, order=order)
        y = filtfilt(b, a, data)
        return y

    @staticmethod
    def compute_fft(data, fs):
        """
        计算信号的FFT变换

        Args:
            data: 输入信号
            fs: 采样率(Hz)

        Returns:
            freqs: 频率数组
            power: 功率谱数组
        """
        n = len(data)
        fft_data = np.fft.fft(data)
        freqs = np.fft.fftfreq(n, 1 / fs)
        return freqs[:n // 2], np.abs(fft_data[:n // 2]) ** 2

    def stacking_average(self, data=[], _axis=0):
        """计算沿指定维度的平均"""
        if data == []:
            data = self.data
        return np.mean(data, axis=_axis)

    def power_spectrum_periodogram(self, x, show_plot=True):
        """
        计算功率谱密度(Periodogram法)

        Args:
            x: 输入信号
            show_plot: 是否显示功率谱图

        Returns:
            f: 频率数组
            Pxx_den: 功率谱密度数组
        """
        f, Pxx_den = signal.periodogram(x, self.fs, window="boxcar", scaling="spectrum")
        if show_plot:
            plt.plot(f, Pxx_den)
            plt.title("Power Spectral Density")
            plt.xlim([0, 60])
            plt.ylim([0, 0.5])
            plt.xlabel("frequency [Hz]")
            plt.ylabel("PSD [V**2]")
            plt.show()
        return f, Pxx_den

    def sum_y(self, x, y, x_inf, x_sup):
        """计算指定频段内的平均功率"""
        sum_A = [y[i] for i, freq in enumerate(x) if x_inf <= freq <= x_sup]
        return np.mean(sum_A)

    def plot_topomap(self, data, ch_names, srate=-1, ch_types="eeg"):
        """绘制地形图"""
        if srate == -1:
            srate = self.fs
        info = mne.create_info(ch_names=ch_names, sfreq=srate, ch_types=ch_types)
        evoked = mne.EvokedArray(data, info)
        evoked.set_montage("standard_1005")
        mne.viz.plot_topomap(evoked.data[:, 0], evoked.info, show=True)

    def signal_noise_ratio(self, data=[], srate=-1, T=[], channel=[], show_plot=True):
        """
        计算信噪比(SNR)

        Args:
            data: 输入数据
            srate: 采样率
            T: 时间长度(ms)
            channel: 通道索引
            show_plot: 是否显示图形

        Returns:
            X1: 频率数组
            snr: 信噪比数组
        """
        if srate == -1:
            srate = self.fs
        num_fft = srate * T
        df = srate / num_fft
        n = np.arange(0, num_fft - 1, 1)
        fx = n * df
        fx = fx[None, :]
        Y = fft(data[channel, :], num_fft)
        Y = np.abs(Y) * 2 / num_fft
        Y = Y[None, :]
        X1 = fx[0, 0: num_fft // 2]
        Y1 = Y[0, 0: num_fft // 2]

        if show_plot:
            plt.plot(X1, Y1)
            plt.title("FFT Transform")
            plt.xlim(0, 60)
            plt.ylim(0, 2)
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Amplitude (μV)")
            plt.show()

        nn1 = np.linspace(5, round(60 / df), round(60 / df), endpoint=False).astype(int)
        snr = []
        for center_freq in nn1:
            if center_freq < round(60 / df):
                noise_power = np.mean(Y1[center_freq - 5: center_freq - 1]) + \
                              np.mean(Y1[center_freq + 1: center_freq + 5])
                signal_power = Y1[center_freq]
                SNR = 20 * np.log10(signal_power / noise_power)
                snr.append(SNR)

        if show_plot:
            plt.plot(X1[0: round(60 / df)], snr)
            plt.title("Signal Noise Ratio")
            plt.xlim(5, 60)
            plt.ylim(-35, 10)
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Signal Noise Ratio (dB)")
            plt.show()
        return X1, snr

    def compute_beta_theta_ratio(self, low_beta, high_beta, theta):
        """
        计算β/θ比值（新增方法）

        Args:
            low_beta: 低β波能量
            high_beta: 高β波能量
            theta: θ波能量

        Returns:
            ratio: β/θ比值
        """
        total_beta = low_beta + high_beta
        return total_beta / theta if theta > 0 else 0