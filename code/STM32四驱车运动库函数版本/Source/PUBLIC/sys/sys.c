/**
* @par Copyright (C): 2010-2019, Shenzhen Yahboom Tech
* @file         sys.c	
* @author       liusen
* @version      V1.0
* @date         2015.01.03
* @brief        系统函数
* @details      
* @par History  
*                 
* version:		liusen_20150103
*/


#include "sys.h"
 
void NVIC_Configuration(void)
{

    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);	//设置NVIC中断分组2:2位抢占优先级，2位响应优先级

}
