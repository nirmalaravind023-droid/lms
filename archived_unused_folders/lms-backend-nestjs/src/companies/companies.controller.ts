import { Controller, Post, Get, Body } from '@nestjs/common';
import { CompaniesService } from './companies.service';

@Controller('companies')
export class CompaniesController {
  constructor(private companiesService: CompaniesService) {}

  @Post()
  async create(@Body() body: any) {
    return this.companiesService.create(body);
  }

  @Get()
  async findAll() {
    return this.companiesService.findAll();
  }
}
