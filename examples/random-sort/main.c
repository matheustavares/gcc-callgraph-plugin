#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "sort.h"

#define ARR_SIZE 10

double *random_array(int N)
{
	double *arr = malloc(N * sizeof(double));
	for (int i = 0; i < N; ++i)
		arr[i] = (double) rand() / RAND_MAX;
	return arr;
}

void print_sorted_info(double *arr, int N)
{
	if (is_sorted(arr, N))
		printf("Array is sorted!\n");
	else
		printf("Array *not* sorted.\n");
}

int main()
{
	double *arr;

	srand((unsigned int)time(NULL));
	arr = random_array(ARR_SIZE);

	print_sorted_info(arr, ARR_SIZE);
	printf("Running random_sort...\n");
	random_sort(arr, ARR_SIZE);
	print_sorted_info(arr, ARR_SIZE);

	free(arr);
	return 0;
}
