#include <stdio.h>

double return_one_double()
{
	return 1.0;
}

int return_two_int()
{
	return (int) (return_one_double() + return_one_double());
}

int main()
{
	double result = .0;
	result += return_one_double();
	result += (double) return_two_int();
	printf("%lf (should be 3)\n", result);
	return 0;
}
