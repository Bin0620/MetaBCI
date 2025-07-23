/**
* @par Copyright (C): 2010-2019, Shenzhen Yahboom Tech
* @file         app_linewalking.c	
* @author       liusen
* @version      V1.0
* @date         2017.07.17
* @brief        巡线模式运动
* @details      
* @par History  见如下说明
*                 
* version:		liusen_20170717
*/
#include "app_linewalking.h"
#include "bsp_linewalking.h"
#include "sys.h"
#include "app_motor.h"
#include "delay.h"
#include "bsp_colorful.h"
#include "usart.h"
/**
* Function       app_LineWalking
* @author        liusen
* @date          2017.07.20    
* @brief         巡线模式运动
* @param[in]     void
* @param[out]    void
* @retval        void
* @par History   无
*/
void app_LineWalking(void)
{
	u8 control_value = 0;      //初始化定义attention值
	u8 speed_value = 0;       //初始化速度修正值
	int LineL1 = 1, LineL2 = 1, LineR1 = 1, LineR2 = 1;			  //初始化巡线四个红外返回值, 都设为HIGH 1	  eg:HIGH:白色   LOW:黑色

	bsp_GetLineWalking(&LineL1, &LineL2, &LineR1, &LineR2);	//获取黑线检测状态
	control_value = receive_del();   //获取当前的attention值	

	if (control_value == 0)
	{
		Colorful_Control(1, 0, 0);
		Car_Stop();	
	}
	else
	{
		//根据attention值设置速度修正值
		speed_value = (control_value - 50) * 100;

		if ((LineL1 == LOW && LineL2 == LOW && LineR1 == LOW && LineR2 == LOW) || (LineL1 == HIGH && LineL2 == HIGH && LineR1 == HIGH && LineR2 == HIGH))
		{	
			Colorful_Control(1, 0, 0);
			Car_Stop();
		}
		else if(LineL1 == LOW ) //左最外侧检测
	    {  	
			Colorful_Control(1, 1, 1);
			Car_SpinLeft(3000 + speed_value, 3000 + speed_value);
			delay_ms(10);
		}
	    else if (LineR2 == LOW) //右最外侧检测
	    {
			Colorful_Control(1, 1, 1);  
			Car_SpinRight(3000 + speed_value,3000 + speed_value);
			delay_ms(10);
		}
	    else if (LineL2 == LOW && LineR1 == HIGH) //中间黑线上的传感器微调车左转
	    {
			Colorful_Control(0, 0, 1);   
			Car_Left(2500 + speed_value);   
		}
		else if (LineL2 == HIGH && LineR1 == LOW) //中间黑线上的传感器微调车右转
	    {
			Colorful_Control(0, 0, 1);   
			Car_Right(2500 + speed_value);
		}
	    else if(LineL2 == LOW && LineR1 == LOW) // 都是黑色, 加速前进
	    {  
			Colorful_Control(0, 1, 0);
			Car_Run(3000 + speed_value);
		}
	}
		
}
