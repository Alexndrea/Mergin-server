// Copyright (C) Lutra Consulting Limited
//
// SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-MerginMaps-Commercial

import {
  LoginData,
  PaginatedUsersParams,
  UserProfileResponse,
  UserResponse /*, getDefaultRetryOptions */
} from '@mergin/lib'
import { AxiosResponse } from 'axios'

import { AdminModule } from '@/modules/admin/module'
import {
  UpdateUserData,
  UsersResponse,
  LatestServerVersionResponse,
  CreateUserData,
  PaginatedAdminProjectsResponse,
  PaginatedAdminProjectsParams,
  ServerUsageResponse,
  DownloadReportParams
} from '@/modules/admin/types'

export const AdminApi = {
  login: (data: LoginData): Promise<AxiosResponse<void>> => {
    return AdminModule.httpService.post('/app/admin/login', data)
  },

  async fetchUsers(
    params: PaginatedUsersParams
  ): Promise<AxiosResponse<UsersResponse>> {
    return AdminModule.httpService.get(`/app/admin/users`, { params })
  },

  async fetchUserByName(
    username: string
  ): Promise<AxiosResponse<UserResponse>> {
    return AdminModule.httpService?.get(`/app/admin/user/${username}`)
  },

  async deleteUser(username: number): Promise<AxiosResponse<void>> {
    return AdminModule.httpService.delete(
      `/app/admin/user/${username}` /*, {
      ...(withRetry ? getDefaultRetryOptions() : {})
    } */
    )
  },

  async updateUser(
    username: string,
    data: UpdateUserData
  ): Promise<AxiosResponse<UserResponse>> {
    return AdminModule.httpService.patch(
      `/app/admin/user/${username}`,
      data /*,
      {
        ...(withRetry ? getDefaultRetryOptions() : {})
      } */
    )
  },

  async getLatestServerVersion(): Promise<
    AxiosResponse<LatestServerVersionResponse>
  > {
    return AdminModule.httpService.get('/v1/latest-version')
  },

  async createUser(
    data: CreateUserData
  ): Promise<AxiosResponse<UserProfileResponse>> {
    return AdminModule.httpService.post(`/app/admin/user`, data)
  },

  async getProjects(
    params: PaginatedAdminProjectsParams
  ): Promise<AxiosResponse<PaginatedAdminProjectsResponse>> {
    return AdminModule.httpService.get('/app/admin/projects', { params })
  },

  /**
   * Permanently delete project
   * @param id project id
   * @return Result promise
   */
  async deleteProject(id: string): Promise<AxiosResponse<void>> {
    return await AdminModule.httpService.delete(`/v2/projects/${id}`)
  },

  /**
   * Restore removed project
   * @param id (String) removed project id
   * @return Result promise
   */
  async restoreProject(id: string): Promise<AxiosResponse<void>> {
    return await AdminModule.httpService.post(
      `/app/project/removed-project/restore/${id}`,
      null
    )
  },

  async getServerUsage(): Promise<AxiosResponse<ServerUsageResponse>> {
    return AdminModule.httpService.get('/app/admin/usage')
  },

  /**
   * Create url for csv file with server statistics
   */
  contructDownloadStatisticsUrl(): string {
    return AdminModule.httpService.absUrl('/app/admin/report')
  },

  async downloadStatistics(
    url: string,
    params: DownloadReportParams
  ): Promise<AxiosResponse<Blob>> {
    return AdminModule.httpService.get(url, {
      responseType: 'blob',
      params
    })
  }
}
