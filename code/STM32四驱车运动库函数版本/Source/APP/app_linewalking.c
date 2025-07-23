/**
* @par Copyright (C): 2010-2019, Shenzhen Yahboom Tech
* @file         app_linewalking.c	
* @author       liusen
* @version      V1.0
* @date         2017.07.17
* @brief        Ѳ��ģʽ�˶�
* @details      
* @par History  ������˵��
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
* @brief         Ѳ��ģʽ�˶�
* @param[in]     void
* @param[out]    void
* @retval        void
* @par History   ��
*/
void app_LineWalking(void)
{
	u8 control_value = 0;      //��ʼ������attentionֵ
	u8 speed_value = 0;       //��ʼ���ٶ�����ֵ
	int LineL1 = 1, LineL2 = 1, LineR1 = 1, LineR2 = 1;			  //��ʼ��Ѳ���ĸ����ⷵ��ֵ, ����ΪHIGH 1	  eg:HIGH:��ɫ   LOW:��ɫ

	bsp_GetLineWalking(&LineL1, &LineL2, &LineR1, &LineR2);	//��ȡ���߼��״̬
	control_value = receive_del();   //��ȡ��ǰ��attentionֵ	

	if (control_value == 0)
	{
		Colorful_Control(1, 0, 0);
		Car_Stop();	
	}
	else
	{
		//����attentionֵ�����ٶ�����ֵ
		speed_value = (control_value - 50) * 100;

		if ((LineL1 == LOW && LineL2 == LOW && LineR1 == LOW && LineR2 == LOW) || (LineL1 == HIGH && LineL2 == HIGH && LineR1 == HIGH && LineR2 == HIGH))
		{	
			Colorful_Control(1, 0, 0);
			Car_Stop();
		}
		else if(LineL1 == LOW ) //���������
	    {  	
			Colorful_Control(1, 1, 1);
			Car_SpinLeft(3000 + speed_value, 3000 + speed_value);
			delay_ms(10);
		}
	    else if (LineR2 == LOW) //���������
	    {
			Colorful_Control(1, 1, 1);  
			Car_SpinRight(3000 + speed_value,3000 + speed_value);
			delay_ms(10);
		}
	    else if (LineL2 == LOW && LineR1 == HIGH) //�м�����ϵĴ�����΢������ת
	    {
			Colorful_Control(0, 0, 1);   
			Car_Left(2500 + speed_value);   
		}
		else if (LineL2 == HIGH && LineR1 == LOW) //�м�����ϵĴ�����΢������ת
	    {
			Colorful_Control(0, 0, 1);   
			Car_Right(2500 + speed_value);
		}
	    else if(LineL2 == LOW && LineR1 == LOW) // ���Ǻ�ɫ, ����ǰ��
	    {  
			Colorful_Control(0, 1, 0);
			Car_Run(3000 + speed_value);
		}
	}
		
}
