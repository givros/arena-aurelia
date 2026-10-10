import * as T from 'three/webgpu';

export type CharacterMergeComponent = {
 name:string; sourceUUID:string; firstVertex:number; vertexCount:number;
 firstIndex:number; indexCount:number; indexed:boolean; colorLinear:number[];
};
export type CharacterMergeGroup = {
 name:string; skinned:boolean; parent:string; triangles:number;
 components:CharacterMergeComponent[];
};
export type CharacterMergeStats = {
 beforeMeshes:number; afterMeshes:number; beforeTriangles:number; afterTriangles:number;
 groups:CharacterMergeGroup[]; skipped:Record<string,number>;
};

const ignoredMaterialKeys=new Set(['uuid','name','color','userData','version','_listeners']);

// Read full material state without Color.toJSON()'s display-space hex conversion.
// Identity/provenance fields do not affect shading; callbacks are separately guarded.
function stateValue(value:any):any {
 if(value===null||typeof value!=='object')return value;
 if(value.isTexture)throw new Error('Textured character primitive is not eligible for this merge.');
 if(value.toArray)return {type:value.constructor.name,values:value.toArray()};
 if(Array.isArray(value))return value.map(stateValue);
 const result:any={};for(const key of Object.keys(value).sort())result[key]=stateValue(value[key]);return result;
}

function materialState(material:T.MeshStandardMaterial){
 if(material.onBeforeCompile!==T.Material.prototype.onBeforeCompile||material.customProgramCacheKey!==T.Material.prototype.customProgramCacheKey)return null;
 const result:any={};
 try{for(const key of Object.keys(material).sort()){
  if(ignoredMaterialKeys.has(key))continue;
  const value=(material as any)[key];if(typeof value==='function')return null;
  result[key]=stateValue(value);
 }}catch{return null;}
 return JSON.stringify(result);
}

function triangles(mesh:T.Mesh){return (mesh.geometry.index?.count??mesh.geometry.getAttribute('position')?.count??0)/3;}

function attributeLayout(geometry:T.BufferGeometry){
 return JSON.stringify(Object.keys(geometry.attributes).sort().map(key=>{
  const a=geometry.getAttribute(key) as T.BufferAttribute;
  return [key,a.array.constructor.name,a.itemSize,a.normalized,a.gpuType,a.usage];
 }));
}

function compatible(a:T.Mesh,b:T.Mesh){
 if(a.parent!==b.parent||!a.matrix.equals(b.matrix)||a.visible!==b.visible||a.layers.mask!==b.layers.mask||a.renderOrder!==b.renderOrder||a.frustumCulled!==b.frustumCulled||a.castShadow!==b.castShadow||a.receiveShadow!==b.receiveShadow)return false;
 if(a.matrixAutoUpdate!==b.matrixAutoUpdate||a.matrixWorldAutoUpdate!==b.matrixWorldAutoUpdate||a.count!==b.count)return false;
 if(!!(a as T.SkinnedMesh).isSkinnedMesh!==!!(b as T.SkinnedMesh).isSkinnedMesh)return false;
 if(!!a.geometry.index!==!!b.geometry.index||attributeLayout(a.geometry)!==attributeLayout(b.geometry))return false;
 if(a.geometry.index&&b.geometry.index&&a.geometry.index.array.constructor!==b.geometry.index.array.constructor)return false;
 if((a as T.SkinnedMesh).isSkinnedMesh){
  const x=a as T.SkinnedMesh,y=b as T.SkinnedMesh;
  if(x.bindMode!==y.bindMode||!x.bindMatrix.equals(y.bindMatrix)||!x.bindMatrixInverse.equals(y.bindMatrixInverse)||x.skeleton.bones.length!==y.skeleton.bones.length)return false;
  if(!x.skeleton.bones.every((bone,i)=>bone===y.skeleton.bones[i]&&x.skeleton.boneInverses[i].equals(y.skeleton.boneInverses[i])))return false;
 }
 return true;
}

function combine(parts:T.Mesh[]):{mesh:T.Mesh;group:CharacterMergeGroup}{
 const first=parts[0],geometry=new T.BufferGeometry();
 const vertexCount=parts.reduce((n,m)=>n+m.geometry.getAttribute('position').count,0);
 const indexCount=parts.reduce((n,m)=>n+(m.geometry.index?.count??m.geometry.getAttribute('position').count),0);
 // Concatenate unchanged typed attribute values. No welding, normalization,
 // resampling, position baking or normal reconstruction is performed.
 for(const key of Object.keys(first.geometry.attributes)){
  const original=first.geometry.getAttribute(key) as T.BufferAttribute;
  const ArrayType=original.array.constructor as any;
  const values=new ArrayType(vertexCount*original.itemSize);let offset=0;
  for(const mesh of parts){const a=mesh.geometry.getAttribute(key) as T.BufferAttribute;values.set(a.array,offset);offset+=a.array.length;}
  const attribute=new T.BufferAttribute(values,original.itemSize,original.normalized);attribute.gpuType=original.gpuType;attribute.setUsage(original.usage);geometry.setAttribute(key,attribute);
 }
 const indexPrototype=first.geometry.index;
 const OriginalIndex=indexPrototype?.array.constructor as any;
 const IndexType=indexPrototype&&vertexCount>65535&&indexPrototype.array.BYTES_PER_ELEMENT<4?Uint32Array:OriginalIndex;
 const indices=indexPrototype?new IndexType(indexCount):null,colors=new Float32Array(vertexCount*3),components:CharacterMergeComponent[]=[];
 let firstVertex=0,firstIndex=0;
 for(const mesh of parts){
  const count=mesh.geometry.getAttribute('position').count,index=mesh.geometry.index,color=(mesh.material as T.MeshStandardMaterial).color;
  if(index)for(let i=0;i<index.count;i++)indices[firstIndex+i]=index.getX(i)+firstVertex;
  for(let i=0;i<count;i++){const at=(firstVertex+i)*3;colors[at]=color.r;colors[at+1]=color.g;colors[at+2]=color.b;}
  components.push({name:mesh.name,sourceUUID:mesh.uuid,firstVertex,vertexCount:count,firstIndex,indexCount:index?.count??count,indexed:!!index,colorLinear:color.toArray()});
  firstVertex+=count;firstIndex+=index?.count??count;
 }
 if(indexPrototype){const index=new T.BufferAttribute(indices,1,indexPrototype.normalized);index.gpuType=indexPrototype.gpuType;index.setUsage(indexPrototype.usage);geometry.setIndex(index);}
 geometry.setAttribute('color',new T.BufferAttribute(colors,3));
 geometry.computeBoundingBox();geometry.computeBoundingSphere();
 const material=(first.material as T.MeshStandardMaterial).clone();material.color.setRGB(1,1,1);material.vertexColors=true;
 material.name='CharacterCompatibleVertexColor';
 const merged=first.clone(false) as T.Mesh;merged.geometry=geometry;merged.material=material;merged.name=first.name+'__CompatibleParts';
 if((merged as T.SkinnedMesh).isSkinnedMesh){(merged as T.SkinnedMesh).boundingBox=null;(merged as T.SkinnedMesh).boundingSphere=null;}
 const group={name:merged.name,skinned:!!(merged as T.SkinnedMesh).isSkinnedMesh,parent:first.parent!.name,triangles:indexCount/3,components};
 merged.userData.characterMerge={version:1,components};
 return {mesh:merged,group};
}

/**
 * Merge compatible opaque parts of a CLONED loaded character prototype.
 * The source GLB and original prototype stay unchanged. Call before creating
 * mixers or palette variants. Keep materialOverride/statue prototypes separate:
 * their uniform stone color must not be multiplied by baked garment colors.
 */
export function mergeCharacterPrimitives(root:T.Object3D,clips:T.AnimationClip[]=[]):CharacterMergeStats{
 root.updateMatrixWorld(true);
 const meshes:T.Mesh[]=[];root.traverse((o:any)=>{if(o.isMesh)meshes.push(o);});
 const stats:CharacterMergeStats={beforeMeshes:meshes.length,afterMeshes:0,beforeTriangles:meshes.reduce((n,m)=>n+triangles(m),0),afterTriangles:0,groups:[],skipped:{}};
 const targets=new Set<string>();for(const clip of clips)for(const track of clip.tracks){try{const parsed=T.PropertyBinding.parseTrackName(track.name);targets.add(parsed.nodeName);}catch{throw new Error('Cannot safely determine character animation track ownership.');}}
 const groups:{state:string,parts:T.Mesh[]}[]=[];
 const skip=(reason:string)=>{stats.skipped[reason]=(stats.skipped[reason]||0)+1;};
 for(const mesh of meshes){
  const g=mesh.geometry,m=mesh.material as T.MeshStandardMaterial;
  if(!mesh.parent||mesh.children.length||Array.isArray(mesh.material)||m.type!=='MeshStandardMaterial'||m.transparent||m.opacity!==1||m.vertexColors||g.hasAttribute('color')){skip('unsupportedMeshOrMaterial');continue;}
  if(/RomanTunic|cloth/i.test(mesh.name+' '+m.name)){skip('paletteTintedTunic');continue;}
  if(targets.has(mesh.name)||targets.has(mesh.uuid)){skip('meshTransformAnimation');continue;}
  if((mesh as any).isInstancedMesh||Object.keys(g.morphAttributes).length||g.groups.length||g.drawRange.start!==0||g.drawRange.count!==Infinity||mesh.onBeforeRender!==T.Object3D.prototype.onBeforeRender||mesh.onAfterRender!==T.Object3D.prototype.onAfterRender||mesh.customDepthMaterial||mesh.customDistanceMaterial){skip('unsupportedDrawBehavior');continue;}
  if(Object.values(g.attributes).some((a:any)=>a.isInterleavedBufferAttribute||a.isInstancedBufferAttribute||a.count!==g.getAttribute('position').count)){skip('unsupportedAttributeLayout');continue;}
  const state=materialState(m);if(state===null){skip('unsupportedMaterialState');continue;}
  if(mesh.matrixAutoUpdate)mesh.updateMatrix();
  let group=groups.find(group=>group.state===state&&compatible(group.parts[0],mesh));
  if(!group){group={state,parts:[]};groups.push(group);}group.parts.push(mesh);
 }
 for(const candidate of groups){
  if(candidate.parts.length<2)continue;
  const parent=candidate.parts[0].parent!,{mesh,group}=combine(candidate.parts),first=parent.children.indexOf(candidate.parts[0]);
  for(const part of candidate.parts)parent.remove(part);
  parent.add(mesh);parent.children.splice(parent.children.indexOf(mesh),1);parent.children.splice(first,0,mesh);
  stats.groups.push(group);
 }
 root.updateMatrixWorld(true);
 root.traverse((o:any)=>{if(o.isMesh){stats.afterMeshes++;stats.afterTriangles+=triangles(o);}});
 if(stats.beforeTriangles!==stats.afterTriangles)throw new Error('Compatible character merge changed the triangle inventory.');
 root.userData.characterMergeStats=stats;
 return stats;
}
