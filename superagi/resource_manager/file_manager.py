import csv
from sqlalchemy.orm import Session
import os
from superagi.helper.resource_helper import ResourceHelper
from superagi.helper.s3_helper import S3Helper
from superagi.lib.logger import logger
from superagi.models.agent import Agent
from superagi.models.agent_execution import AgentExecution
from superagi.types.storage_types import StorageType

class UnsupportedFileTypeError(Exception):
    pass

class FileManager:
    def __init__(self, session: Session, agent_id: int = None, agent_execution_id: int = None):
        self.session = session
        self.agent_id = agent_id
        self.agent_execution_id = agent_execution_id
        
    def write_binary_file(self, file_name: str, data):
        if self.agent_id is not None:
            final_path = ResourceHelper.get_agent_write_resource_path(file_name,
                                                                      Agent.get_agent_from_id(self.session,
                                                                                              self.agent_id),
                                                                      AgentExecution.get_agent_execution_from_id(
                                                                          self.session,
                                                                          self.agent_execution_id))
        else:
            final_path = ResourceHelper.get_resource_path(file_name)
        try:
            with open(final_path, mode="wb") as img:
                img.write(data)
                img.close()
            self.write_to_s3(file_name, final_path)
            logger.info(f"Binary {file_name} saved successfully")
            return f"Binary {file_name} saved successfully"
        except Exception as err:
            return f"Error write_binary_file: {err}"
        
    def write_to_s3(self, file_name, final_path):
        with open(final_path, 'rb') as img:
            resource = ResourceHelper.make_written_file_resource(file_name=file_name,
                                                                 agent=Agent.get_agent_from_id(self.session,
                                                                                               self.agent_id),
                                                                 agent_execution=AgentExecution
                                                                 .get_agent_execution_from_id(self.session,
                                                                                              self.agent_execution_id),
                                                                 session=self.session)
            if resource.storage_type == StorageType.S3.value:
                s3_helper = S3Helper()
                s3_helper.upload_file(img, path=resource.path)

    def write_file(self, file_name: str, content, return_file_path: bool = False):
        if self.agent_id is not None:
            final_path = ResourceHelper.get_agent_write_resource_path(file_name,
                                                                      agent=Agent.get_agent_from_id(self.session,
                                                                                                    self.agent_id),
                                                                      agent_execution=AgentExecution
                                                                      .get_agent_execution_from_id(self.session,
                                                                                                   self.agent_execution_id))
        else:
            final_path = ResourceHelper.get_resource_path(file_name)
        
        try:
            self.save_file_by_type(file_name=file_name, file_path=final_path, content=content)
        except Exception as err:
            return f"Error write_file: {err}"
        
        if return_file_path:
            return final_path
        else:
            return f"{file_name} - File written successfully"
        
    def write_csv_file(self, file_name: str, final_path: str, csv_data) -> str:
        try:
            with open(final_path, mode="w") as file:
                writer = csv.writer(file, lineterminator="\n")
                for row in csv_data:
                    writer.writerows(row)
            self.write_to_s3(file_name, final_path)
            logger.info(f"{file_name} - File written successfully")
            return f"{file_name} - File written successfully"
        except Exception as err:
            return f"Error write_csv_file: {err}"
        
    def write_pdf_file(self, file_name: str ,file_path: str, content):
        pass
    
    def write_docx_file(self, file_name: str ,file_path: str, content):
        pass
    
    def write_txt_file(self, file_name: str ,file_path: str, content) -> str:
        try:
            with open(file_path, mode="w") as file:
                file.write(content)
                file.close()
            self.write_to_s3(file_name, file_path)
            logger.info(f"{file_name} - File written successfully")
            return file_path
        except Exception as err:
            return f"Error write_file: {err}"
    
    def get_agent_resource_path(self, file_name: str):
        return ResourceHelper.get_agent_write_resource_path(file_name, agent=Agent.get_agent_from_id(self.session,
                                                                                                     self.agent_id),
                                                            agent_execution=AgentExecution
                                                            .get_agent_execution_from_id(self.session,
                                                                                         self.agent_execution_id))
        
    def read_file(self, file_name: str):
        if self.agent_id is not None:
            final_path = self.get_agent_resource_path(file_name)
        else:
            final_path = ResourceHelper.get_resource_path(file_name)

        try:
            with open(final_path, mode="r") as file:
                content = file.read()
            logger.info(f"{file_name} - File read successfully")
            return content
        except Exception as err:
            return f"Error while reading file {file_name}: {err}"
        
    def get_files(self):
        """
        Gets all file names generated by the CodingTool.
        Returns:
            A list of file names.
        """
        
        if self.agent_id is not None:
            final_path = self.get_agent_resource_path("")
        else:
            final_path = ResourceHelper.get_resource_path("")
        try:
            # List all files in the directory
            files = os.listdir(final_path)
        except Exception as err:
            logger.error(f"Error while accessing files in {final_path}: {err}")
            files = []
        return files

    def save_file_by_type(self, file_name: str, file_path: str, content):
        
        # Extract the file type from the file_name
        file_type = file_name.split('.')[-1].lower()
        
        # Dictionary to map file types to corresponding functions
        file_type_handlers = {
            'txt': write_txt_file,
            'pdf': write_pdf_file,
            'docx': write_docx_file, 
            'csv': write_csv_file,
            'html': write_txt_file
            # NOTE: Add more file types and corresponding functions as needed, These functions should be defined 
        }
        
        if file_path in file_type_handlers:
            return file_type_handlers[file_type](file_name, file_path, content)
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {file_type}. Cannot save the file.")
        